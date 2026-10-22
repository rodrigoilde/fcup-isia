"""AEDHubAgent: the hub of one cell (D1). Plays IncidentVerifier, IncidentCoordinator (one CaseFSM per
case, agents/case_fsm.py), AEDCustodian (its own cabinet) and ReputationManager (its trust table).

Handled whatever their thread (service requests):
  P25 registrations · P11/P12/P20 AED custody · P22 trust queries · P23 reputation summaries ·
  P26 candidate notices · P27 heartbeats and case snapshots.
New alerts (P01) join an open candidate of the same cell within the merge window (_MergeCandidates),
or open a new one, which is announced to the neighbouring hubs (P26).

Failover (D8): every hub sends heartbeats and snapshots of its declared cases to its successor (its
lowest-id neighbour that answers). A successor that hears nothing for the lease time takes the cases
over (P28). Hubs fail by crash (fault injection); partitions of the fixed infrastructure are out of
scope, which is what keeps a single owner per case (OS1) without a consensus protocol.
"""

import itertools

from ..behaviours.aed_custody import AEDCustody
from ..behaviours.reputation import TrustTable
from ..protocol.messages import (AEDRelease, AEDReservation, AEDReservationCancel, AEDReservationRefusal,
                                 AEDReservationRequest, AEDRetrieval, AEDRetrievalFailure, AEDUnlock, AlertCancel,
                                 AlertReport, CandidateMerge, CandidateNotice, CaseSnapshot, Deregistration,
                                 Heartbeat, HeartbeatAck, Registration, RegistrationAck, ReputationSummary,
                                 TrustQuery, TrustReply)
from ..protocol.ontology import AEDState, CaseState
from ..sim.directory import Directory
from .base import CEMRAgent, Incoming
from .case_fsm import CaseFSM


class AEDHubAgent(CEMRAgent):
    KIND = "hub"

    def __init__(self, hub_id: int, ctx):
        super().__init__(Directory.hub(hub_id), ctx, ctx.world.grid.hub_positions[hub_id])
        self.hub_id = hub_id

    async def on_setup(self):
        cfg = self.cfg
        self.registry: dict[str, dict[str, dict]] = {"volunteer": {}, "witness": {}, "sensor": {}}
        self.trust = TrustTable(enabled=cfg["policy"]["reputation"] and cfg["policy"]["allocation"] != "naive",
                                peer_discount=cfg["reputation"]["peer_discount"])
        layout = self.world.layout
        self.custody = AEDCustody(self.hub_id, layout.aed_faulty[self.hub_id], self.rng,
                                  closed=layout.aed_closed.get(self.hub_id, False))
        self._publish_aed_state()
        self.open_cases: dict[str, CaseFSM] = {}
        self.relays: dict[str, tuple[str, str]] = {}           # alert id -> (keeper hub, keeper case) after P26
        self._case_ids = itertools.count(1)
        self.neighbours = sorted(self.world.grid.neighbours[self.hub_id])
        # P27: owner side
        self.successor_index = 0
        self.last_ack = 0.0
        # P27: successor side
        self.replicas: dict[str, dict[str, CaseSnapshot]] = {}  # owner -> case -> snapshot
        self.last_heartbeat: dict[str, float] = {}
        self.taken_over: set[str] = set()
        self.service_handlers = {
            Registration: self.on_registration,
            Deregistration: self.on_deregistration,
            AEDReservationRequest: self.on_reserve,
            AEDReservationCancel: self.on_reservation_cancel,
            AEDRetrieval: self.on_retrieve,
            AEDRelease: self.on_aed_release,
            TrustQuery: self.on_trust_query,
            ReputationSummary: self.on_reputation_summary,
            CandidateNotice: self.on_candidate_notice,
            Heartbeat: self.on_heartbeat,
            HeartbeatAck: self.on_heartbeat_ack,
            CaseSnapshot: self.on_snapshot,
        }
        rep, fo = cfg["reputation"], cfg["failover"]
        if self.trust.enabled:
            self.every(rep["decay_period_s"], self.decay_trust, "decay_trust")                 # _DecayTrust
            self.every(rep["gossip_period_s"], self.share_reputation, "share_reputation")     # P23
        self.every(fo["heartbeat_s"], self.heartbeat, "heartbeat")                            # P27
        self.every(fo["heartbeat_s"], self.watch_predecessors, "watch_predecessors")

    # --- P01: new alerts ----------------------------------------------------------------------
    async def on_message(self, inc: Incoming) -> None:
        p = inc.payload
        if isinstance(p, (AlertReport, AlertCancel)) and inc.thread in self.relays:
            await self.relay(inc)
        elif isinstance(p, AlertReport):
            await self.on_new_alert(inc, p)
        elif isinstance(p, AlertCancel):
            self.log("late_cancel", alert=p.alert_id, source=inc.sender)
        elif isinstance(p, CandidateMerge):
            self.log("late_merge", candidate=p.candidate_id, keeper=p.keeper_id)
        else:
            await super().on_message(inc)

    async def on_new_alert(self, inc: Incoming, report: AlertReport) -> None:
        now = self.now()
        window = self.cfg["verification"]["merge_window_s"]
        for fsm in self.open_cases.values():
            case = fsm.case
            if (case.cell == report.cell and now - case.t_open <= window
                    and case.state not in (CaseState.CLOSED, CaseState.DISCARDED) and case.merged_into is None):
                self.claim(report.alert_id, fsm)
                await fsm.enqueue(inc.msg)
                self.log("alert_merged", case=case.case_id, alert=report.alert_id, source=inc.sender)
                return
        case_id = f"{self.label}-c{next(self._case_ids)}"
        fsm = CaseFSM(self, case_id, report.cell, report.event_type)
        self.open_cases[case_id] = fsm
        self.open_conversation(fsm)
        self.claim(report.alert_id, fsm)
        await fsm.enqueue(inc.msg)
        self.log("candidate_opened", case=case_id, cell=report.cell, alert=report.alert_id, source=inc.sender,
                 event_type=report.event_type)

    def case_finished(self, fsm: CaseFSM) -> None:
        self.open_cases.pop(fsm.case.case_id, None)

    # --- P26: duplicates across cell borders ----------------------------------------------------
    async def announce_candidate(self, fsm: CaseFSM) -> None:
        case = fsm.case
        event = next(iter(case.sources.values())).event_type or ""
        for hub_id in self.neighbours:
            await self.send_to(Directory.hub(hub_id), CandidateNotice(case.case_id, case.cell, case.t_open, event),
                               thread=case.case_id)

    async def on_candidate_notice(self, inc: Incoming) -> None:
        """Keep the candidate opened first (ties: lower hub id); if that is the other one, drop ours."""
        notice: CandidateNotice = inc.payload
        theirs = (notice.t_open, Directory.hub_id(inc.sender))
        window = self.cfg["verification"]["merge_window_s"]
        near = set(self.world.grid.neighbours[notice.cell]) | {notice.cell}
        for fsm in list(self.open_cases.values()):
            case = fsm.case
            if (case.state == CaseState.VERIFYING and case.merged_into is None and case.cell in near
                    and abs(case.t_open - notice.t_open) <= window and theirs < (case.t_open, self.hub_id)):
                await fsm.enqueue(inc.msg)          # the FSM sees the notice and drops itself
                return

    async def drop_duplicate(self, fsm: CaseFSM) -> None:
        keeper_hub, keeper_case = fsm.case.merged_into
        alerts = [{"origin": origin, "report": report} for origin, report in fsm.case.alert_reports.values()]
        await self.send_to(keeper_hub, CandidateMerge(fsm.case.case_id, keeper_case, alerts), thread=keeper_case)
        for alert_id in fsm.case.alerts:
            self.relays[alert_id] = (keeper_hub, keeper_case)

    async def relay(self, inc: Incoming) -> None:
        keeper_hub, _ = self.relays[inc.thread]
        payload = inc.payload
        payload.origin = payload.origin or inc.sender
        await self.send_to(keeper_hub, payload, thread=inc.thread)

    # --- P25: registry -----------------------------------------------------------------------
    async def on_registration(self, inc: Incoming) -> None:
        reg: Registration = inc.payload
        for role_table in self.registry.values():
            role_table.pop(inc.sender, None)
        self.registry[reg.role][inc.sender] = {"ring": reg.ring, "qualification": reg.qualification,
                                               "cell": reg.cell, "t": self.now()}
        await self.reply(inc, RegistrationAck(self.hub_id))

    async def on_deregistration(self, inc: Incoming) -> None:
        self.registry.get(inc.payload.role, {}).pop(inc.sender, None)

    def registered(self, role: str, max_ring: int) -> list[str]:
        return sorted(name for name, info in self.registry[role].items() if info["ring"] <= max_ring)

    # --- P11 / P12 / P20: AED custody ----------------------------------------------------------
    def _publish_aed_state(self) -> None:
        self.world.set_aed_state(self.hub_id, str(self.custody.state), by_hub=self.hub_id)

    async def on_reserve(self, inc: Incoming) -> None:
        req: AEDReservationRequest = inc.payload
        self.custody.expire(self.now())
        prior = str(self.custody.state)
        ok, result = self.custody.reserve(req.case_id, req.award_token, req.valid_for_s, self.now())
        self.log("aed_reserve", aed=self.hub_id, case=req.case_id, granted=ok, result=result, prior_state=prior)
        self._publish_aed_state()
        if ok:
            await self.reply(inc, AEDReservation(req.case_id, self.hub_id, result,
                                                 self.custody.reservation.expires_at))
        else:
            await self.reply(inc, AEDReservationRefusal(req.case_id, self.hub_id, result))

    async def on_reservation_cancel(self, inc: Incoming) -> None:
        if self.custody.cancel(inc.payload.reservation_ref):
            self._publish_aed_state()
            self.log("aed_reservation_cancelled", aed=self.hub_id, case=inc.payload.case_id)

    async def on_retrieve(self, inc: Incoming) -> None:
        req: AEDRetrieval = inc.payload
        ok, result = self.custody.retrieve(req.reservation_ref, req.award_token, self.now())
        self._publish_aed_state()
        if ok:
            await self.reply(inc, AEDUnlock(req.case_id, self.hub_id, result))
        else:
            await self.reply(inc, AEDRetrievalFailure(req.case_id, self.hub_id, result))
        self.log("aed_retrieve", aed=self.hub_id, case=req.case_id, by=inc.sender, ok=ok,
                 reason=None if ok else result)

    async def on_aed_release(self, inc: Incoming) -> None:
        state = self.custody.release(inc.payload.reservation_ref)
        self._publish_aed_state()
        self.log("aed_released", aed=self.hub_id, case=inc.payload.case_id, state=str(state))
        if state == AEDState.UNAVAILABLE:
            async def restock():
                await self.sleep(self.cfg["aed"]["restock_s"])
                self.custody.restock()
                self._publish_aed_state()
            self.spawn(restock, "aed_restock")

    # --- P21 / P22 / P23: reputation ----------------------------------------------------------
    def apply_outcome(self, case_id: str, labels: list[dict]) -> None:
        if not self.trust.enabled:
            return
        for label in labels:
            trust = self.trust.update(label["pseudonym"], label["success"], label.get("weight", 1.0))
            self.log("trust_update", case=case_id, pseudonym=label["pseudonym"], role=label["kind"],
                     success=label["success"], trust=round(trust, 3))

    async def on_trust_query(self, inc: Incoming) -> None:
        names = inc.payload.pseudonyms
        await self.reply(inc, TrustReply({n: {"trust": self.trust.trust(n), "n": self.trust.observations(n)}
                                          for n in names}))

    async def decay_trust(self) -> None:
        self.trust.decay(self.cfg["reputation"]["decay_factor"])

    async def share_reputation(self) -> None:
        entries = self.trust.summary()
        if entries:
            for hub_id in self.neighbours:
                await self.send_to(Directory.hub(hub_id), ReputationSummary(entries), thread=f"rep-{self.label}")

    async def on_reputation_summary(self, inc: Incoming) -> None:
        if self.trust.enabled:
            self.trust.merge(inc.sender, inc.payload.entries)

    # --- P27 / P28: replication and failover -----------------------------------------------------
    @property
    def successor(self) -> str:
        return Directory.hub(self.neighbours[self.successor_index % len(self.neighbours)])

    async def replicate(self, snapshot: CaseSnapshot) -> None:
        await self.send_to(self.successor, snapshot, thread=snapshot.case_id)

    async def heartbeat(self) -> None:
        fo = self.cfg["failover"]
        now = self.now()
        lease = fo["heartbeat_s"] * fo["lease_heartbeats"]
        if self.last_ack and now - self.last_ack > lease:        # successor silent: switch to the next one
            self.successor_index += 1
            self.last_ack = now
            self.log("successor_changed", successor=self.successor)
            for fsm in list(self.open_cases.values()):
                await fsm.replicate()
        if not self.last_ack:
            self.last_ack = now
        open_cases = sorted(c for c, fsm in self.open_cases.items() if fsm.declared)
        await self.send_to(self.successor, Heartbeat(open_cases, now + lease), thread=f"hb-{self.label}")

    async def on_heartbeat(self, inc: Incoming) -> None:
        self.last_heartbeat[inc.sender] = self.now()
        owned = set(inc.payload.open_cases)
        for case_id in [c for c in self.replicas.get(inc.sender, {}) if c not in owned]:
            del self.replicas[inc.sender][case_id]                  # closed since the snapshot
        await self.reply(inc, HeartbeatAck(inc.payload.lease_until))

    async def on_heartbeat_ack(self, inc: Incoming) -> None:
        self.last_ack = self.now()

    async def on_snapshot(self, inc: Incoming) -> None:
        snap: CaseSnapshot = inc.payload
        self.last_heartbeat.setdefault(inc.sender, self.now())
        cases = self.replicas.setdefault(inc.sender, {})
        if snap.closed:
            cases.pop(snap.case_id, None)
        else:
            cases[snap.case_id] = snap

    async def watch_predecessors(self) -> None:
        """Take over the cases of a hub whose heartbeats stopped for longer than the lease (+ margin)."""
        fo = self.cfg["failover"]
        limit = fo["heartbeat_s"] * (fo["lease_heartbeats"] + fo["takeover_margin_heartbeats"])
        now = self.now()
        for owner, last in list(self.last_heartbeat.items()):
            if owner in self.taken_over or now - last <= limit:
                continue
            self.taken_over.add(owner)
            cases = self.replicas.pop(owner, {})
            self.log("takeover", previous=owner, cases=sorted(cases), silent_for=round(now - last, 1))
            for snap in cases.values():
                fsm = CaseFSM.from_snapshot(self, snap, owner)
                self.open_cases[snap.case_id] = fsm
                self.open_conversation(fsm)

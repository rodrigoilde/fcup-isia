"""AEDHubAgent: o hub de uma célula (decisão D1), no armário de DAE dessa célula.

Papéis: IncidentVerifier e IncidentCoordinator (uma CaseFSM por caso, em `case_fsm`), AEDCustodian
(o seu armário) e ReputationManager (a sua tabela de confiança). Tratados seja qual for a thread
(pedidos de serviço): registos P25, custódia do DAE P11/P12/P20, resumos de reputação P23, avisos
de candidato P26 e heartbeats e réplicas P27 (em `hub_failover`).

Um alerta novo (P01) junta-se a um candidato aberto da mesma célula e da mesma área (~100 m) dentro
da janela de fusão (_MergeCandidates), ou abre um candidato novo, anunciado aos hubs vizinhos (P26).
Desenho em docs/02-architectural-design.md §2 e docs/03-detailed-design.md §3.
"""

import itertools

from ..behaviours.aed_custody import AEDCustody
from ..behaviours.reputation import TrustTable
from ..behaviours.verification import Belief, Candidate, notice_decision, same_incident
from ..protocol.messages_detection import AlertCancel, AlertReport
from ..protocol.messages_hubs import (CandidateMerge, CandidateNotice, CaseSnapshot, Deregistration, Heartbeat,
                                      HeartbeatAck, Registration, RegistrationAck, ReputationSummary)
from ..protocol.messages_response import (AEDRelease, AEDReservation, AEDReservationCancel, AEDReservationRefusal,
                                          AEDReservationRequest, AEDRetrieval, AEDRetrievalFailure, AEDUnlock)
from ..protocol.ontology import AEDState, CaseState
from ..sim.directory import Directory
from .base import CEMRAgent
from .case_fsm import CaseFSM
from .case_record import CaseRecord
from .conversation import Incoming
from .hub_failover import HubFailover


class AEDHubAgent(CEMRAgent):
    """Hub de célula: agente híbrido em camadas (Wooldridge, 2009).

    A camada reativa são os handlers de serviço (router, custódia do DAE, heartbeats); a camada
    deliberativa é uma FSM por caso, com fusão bayesiana da evidência e Contract Net.

    Attributes:
        hub_id (int): Id da célula.
        registry (dict): Papel -> agente -> {ring, qualification, cell, t} dos registados (P25).
        trust (TrustTable): Tabela de confiança (D6).
        custody (AEDCustody): Estado do armário de DAE.
        open_cases (dict[str, CaseFSM]): Casos abertos por id.
        relays (dict[str, tuple]): Alerta -> (hub, caso) que ficou com ele depois de uma fusão P26.
        neighbours (list[int]): Células vizinhas, por id.
        failover (HubFailover): Replicação e recuperação (D8).
    """

    KIND = "hub"

    def __init__(self, hub_id: int, ctx):
        super().__init__(Directory.hub(hub_id), ctx, ctx.world.grid.hub_positions[hub_id])
        self.hub_id = hub_id

    async def on_setup(self) -> None:
        cfg = self.cfg
        self.registry: dict[str, dict[str, dict]] = {"volunteer": {}, "witness": {}, "sensor": {}}
        reputation_on = cfg["policy"]["reputation"] and cfg["policy"]["allocation"] != "naive"
        self.trust = TrustTable(enabled=reputation_on, peer_discount=cfg["reputation"]["peer_discount"])
        layout = self.world.layout
        self.custody = AEDCustody(self.hub_id, layout.aed_faulty[self.hub_id], self.rng,
                                  closed=layout.aed_closed.get(self.hub_id, False))
        self.publish_aed_state()
        self.open_cases: dict[str, CaseFSM] = {}
        self.relays: dict[str, tuple[str, str]] = {}
        self.case_ids = itertools.count(1)
        self.neighbours = sorted(self.world.grid.neighbours[self.hub_id])
        self.failover = HubFailover(self)
        self.service_handlers = {
            Registration: self.on_registration,
            Deregistration: self.on_deregistration,
            AEDReservationRequest: self.on_reserve,
            AEDReservationCancel: self.on_reservation_cancel,
            AEDRetrieval: self.on_retrieve,
            AEDRelease: self.on_aed_release,
            ReputationSummary: self.on_reputation_summary,
            CandidateNotice: self.on_candidate_notice,
            Heartbeat: self.failover.on_heartbeat,
            HeartbeatAck: self.failover.on_heartbeat_ack,
            CaseSnapshot: self.failover.on_snapshot,
        }
        rep = cfg["reputation"]
        heartbeat_s = cfg["failover"]["heartbeat_s"]
        if self.trust.enabled:
            self.every(rep["decay_period_s"], self.decay_trust, "decay_trust")                 # _DecayTrust
            self.every(rep["gossip_period_s"], self.share_reputation, "share_reputation")     # P23
        self.every(heartbeat_s, self.failover.heartbeat, "heartbeat")                         # P27
        self.every(heartbeat_s, self.failover.watch_predecessors, "watch_predecessors")       # P28

    # --- P01: alertas novos -----------------------------------------------------------------------
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

    def open_candidate_for(self, report: AlertReport) -> CaseFSM | None:
        """_MergeCandidates: um candidato aberto do mesmo incidente (mesma célula, perto no tempo e na área).

        Fundir só por célula juntava num caso doentes diferentes da mesma célula (C3).
        """
        vcfg = self.cfg["verification"]
        for fsm in self.open_cases.values():
            case = fsm.case
            if case.state in (CaseState.CLOSED, CaseState.DISCARDED) or case.merged_into is not None:
                continue
            same = same_incident(case.area, case.t_open, report.area, self.now(), vcfg["merge_window_s"],
                                 vcfg["merge_radius_m"])
            if case.cell == report.cell and same:
                return fsm
        return None

    async def on_new_alert(self, inc: Incoming, report: AlertReport) -> None:
        """Junta o alerta a um candidato aberto ou abre um candidato novo."""
        fsm = self.open_candidate_for(report)
        if fsm is not None:
            self.claim(report.alert_id, fsm)
            await fsm.enqueue(inc.msg)
            self.log("alert_merged", case=fsm.case.case_id, alert=report.alert_id, source=inc.sender)
            return
        case_id = f"{self.label}-c{next(self.case_ids)}"
        prior = Belief(self.cfg["verification"]["prior"])
        record = CaseRecord(case_id, report.cell, report.area, self.now(), prior, first_event_type=report.event_type)
        fsm = CaseFSM(self, record)
        self.open_cases[case_id] = fsm
        self.open_conversation(fsm)
        self.claim(report.alert_id, fsm)
        await fsm.enqueue(inc.msg)
        self.log("candidate_opened", case=case_id, cell=report.cell, alert=report.alert_id, source=inc.sender,
                 event_type=report.event_type)

    def case_finished(self, fsm: CaseFSM) -> None:
        """Esquece um caso cuja FSM terminou."""
        self.open_cases.pop(fsm.case.case_id, None)

    # --- P26: duplicados na fronteira entre células ------------------------------------------------
    @staticmethod
    def notice_for(fsm: CaseFSM) -> CandidateNotice:
        """O aviso P26 de um candidato nosso."""
        case = fsm.case
        return CandidateNotice(case.case_id, case.cell, case.area, case.t_open, case.first_event_type)

    async def announce_candidate(self, fsm: CaseFSM) -> None:
        """Anuncia um candidato novo aos hubs vizinhos."""
        notice = self.notice_for(fsm)
        for hub_id in self.neighbours:
            await self.send_to(Directory.hub(hub_id), notice, thread=fsm.case.case_id)

    async def on_candidate_notice(self, inc: Incoming) -> None:
        """P26: fica o candidato aberto primeiro (em empate, o do hub de menor id).

        Se o nosso é o mais recente, larga-o; se é o mais antigo, responde com o nosso aviso para o
        outro hub largar o dele. Antes só agia o hub com o candidato mais recente, e se esse tivesse
        aberto o seu depois do aviso do outro nunca chegava a saber dele (casos duplicados).
        """
        notice: CandidateNotice = inc.payload
        vcfg = self.cfg["verification"]
        theirs = Candidate(notice.t_open, Directory.hub_id(inc.sender), notice.area)
        for fsm in list(self.open_cases.values()):
            case = fsm.case
            if case.merged_into is not None or case.state in (CaseState.CLOSED, CaseState.DISCARDED):
                continue
            ours = Candidate(case.t_open, self.hub_id, case.area)
            decision = notice_decision(ours, theirs, vcfg["merge_window_s"], vcfg["merge_radius_m"])
            if decision == "drop" and case.state == CaseState.VERIFYING:
                await fsm.enqueue(inc.msg)          # a FSM vê o aviso e descarta-se
                return
            if decision == "reply":
                await self.send_to(inc.sender, self.notice_for(fsm), thread=case.case_id)
                self.log("duplicate_notified", case=case.case_id, other=notice.candidate_id, hub=inc.sender)
                return

    async def drop_duplicate(self, fsm: CaseFSM) -> None:
        """Passa os alertas do candidato largado ao hub que ficou com o incidente e reencaminha os seguintes."""
        keeper_hub, keeper_case = fsm.case.merged_into
        alerts = [{"origin": origin, "report": report} for origin, report in fsm.case.alert_reports.values()]
        await self.send_to(keeper_hub, CandidateMerge(fsm.case.case_id, keeper_case, alerts), thread=keeper_case)
        for alert_id in fsm.case.alerts:
            self.relays[alert_id] = (keeper_hub, keeper_case)

    async def relay(self, inc: Incoming) -> None:
        """Reencaminha um alerta de um candidato largado, com a fonte original."""
        keeper_hub, _ = self.relays[inc.thread]
        payload = inc.payload
        payload.origin = payload.origin or inc.sender
        await self.send_to(keeper_hub, payload, thread=inc.thread)

    # --- P25: registo ------------------------------------------------------------------------------
    async def on_registration(self, inc: Incoming) -> None:
        """P25 (subscribe): guarda quem se registou, sem coordenadas (D3)."""
        reg: Registration = inc.payload
        for role_table in self.registry.values():
            role_table.pop(inc.sender, None)
        self.registry[reg.role][inc.sender] = {"ring": reg.ring, "qualification": reg.qualification,
                                               "cell": reg.cell, "t": self.now()}
        await self.reply(inc, RegistrationAck(self.hub_id))

    async def on_deregistration(self, inc: Incoming) -> None:
        """P25 (cancel)."""
        self.registry.get(inc.payload.role, {}).pop(inc.sender, None)

    def registered(self, role: str, max_ring: int) -> list[str]:
        """Agentes registados com um papel, até ao anel `max_ring`."""
        return sorted(name for name, info in self.registry[role].items() if info["ring"] <= max_ring)

    # --- P11 / P12 / P20: custódia do DAE ------------------------------------------------------------
    def publish_aed_state(self) -> None:
        """Atualiza o estado do DAE no registo público (só o próprio hub o pode fazer)."""
        self.world.set_aed_state(self.hub_id, str(self.custody.state), by_hub=self.hub_id)

    async def on_reserve(self, inc: Incoming) -> None:
        """P11: reserva o DAE para um caso (OS3: no máximo uma reserva ativa)."""
        req: AEDReservationRequest = inc.payload
        self.custody.expire(self.now())
        prior = str(self.custody.state)
        ok, result = self.custody.reserve(req.case_id, req.award_token, req.valid_for_s, self.now())
        self.log("aed_reserve", aed=self.hub_id, case=req.case_id, granted=ok, result=result, prior_state=prior)
        self.publish_aed_state()
        if ok:
            expires_at = self.custody.reservation.expires_at
            await self.reply(inc, AEDReservation(req.case_id, self.hub_id, result, expires_at))
        else:
            await self.reply(inc, AEDReservationRefusal(req.case_id, self.hub_id, result))

    async def on_reservation_cancel(self, inc: Incoming) -> None:
        """P11 (cancel)."""
        if self.custody.cancel(inc.payload.reservation_ref):
            self.publish_aed_state()
            self.log("aed_reservation_cancelled", aed=self.hub_id, case=inc.payload.case_id)

    async def on_retrieve(self, inc: Incoming) -> None:
        """P12: abre o armário ao estafeta adjudicado."""
        req: AEDRetrieval = inc.payload
        ok, result = self.custody.retrieve(req.reservation_ref, req.award_token, self.now())
        self.publish_aed_state()
        if ok:
            await self.reply(inc, AEDUnlock(req.case_id, self.hub_id, result))
        else:
            await self.reply(inc, AEDRetrievalFailure(req.case_id, self.hub_id, result))
        self.log("aed_retrieve", aed=self.hub_id, case=req.case_id, by=inc.sender, ok=ok,
                 reason=None if ok else result)

    async def on_aed_release(self, inc: Incoming) -> None:
        """P20: o caso fechou; um DAE usado fica fora de serviço até ser reposto."""
        state = self.custody.release(inc.payload.reservation_ref)
        self.publish_aed_state()
        self.log("aed_released", aed=self.hub_id, case=inc.payload.case_id, state=str(state))
        if state == AEDState.UNAVAILABLE:
            self.spawn(self.restock, "aed_restock")

    async def restock(self) -> None:
        """Reposição do DAE, passado o tempo de verificação."""
        await self.sleep(self.cfg["aed"]["restock_s"])
        self.custody.restock()
        self.publish_aed_state()

    # --- P21 / P23: reputação -------------------------------------------------------------------------
    def apply_outcome(self, case_id: str, labels: list[dict]) -> None:
        """P21: junta os rótulos de resultado à tabela de confiança."""
        if not self.trust.enabled:
            return
        for label in labels:
            trust = self.trust.update(label["pseudonym"], label["success"], label.get("weight", 1.0))
            self.log("trust_update", case=case_id, pseudonym=label["pseudonym"], role=label["kind"],
                     success=label["success"], trust=round(trust, 3))

    async def decay_trust(self) -> None:
        """_DecayTrust: aproxima as contagens do prior."""
        self.trust.decay(self.cfg["reputation"]["decay_factor"])

    async def share_reputation(self) -> None:
        """P23: envia as contagens próprias aos hubs vizinhos."""
        entries = self.trust.summary()
        if not entries:
            return
        for hub_id in self.neighbours:
            await self.send_to(Directory.hub(hub_id), ReputationSummary(entries), thread=f"rep-{self.label}")

    async def on_reputation_summary(self, inc: Incoming) -> None:
        """P23: guarda o resumo mais recente de um vizinho."""
        if self.trust.enabled:
            self.trust.merge(inc.sender, inc.payload.entries)

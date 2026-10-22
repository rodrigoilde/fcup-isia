"""Life cycle of one candidate/case inside its hub: the IncidentVerifier and IncidentCoordinator roles.

States (FSMBehaviour) and the liveness they implement (analysis §5.2, R3 and R4):

    VERIFY   = RaiseCandidateAlert . _MergeCandidates . CandidateOpen . _OpenWindow .
               (Gather || [ActivateGuidance]) . _FuseEvidence . _ClassifyPriority . _LogDecision .
               (DeclareIncident | _DiscardCandidate . [CloseCase])
    DISPATCH = DeclareIncident . _AssessNeeds . RequestDisclosure .
               ([RequestAmbulance] || Recruit+ || [_SelectAED . ReserveAED]) . HelpEnRouteNotice
    TRACK    = (StatusUpdate . _MonitorProgress . [Recruit | ReleaseResponder])+ . [RetractIncident]
    CLOSE    = CloseCase . OutcomeFeedback
    DISCARD  = _DiscardCandidate . [CloseCase] . [OutcomeFeedback]

Every message of the case carries thread = case id, except alerts, which keep their own alert id
as thread; the hub claims those threads for the case when it merges an alert. A declared case is
replicated to the hub's successor after every relevant change (P27, D8); a successor that takes
over rebuilds the case from that snapshot and starts in TRACK.

Policy "naive" (baseline B1): no verification (declare on the first alert), call every volunteer up to
ring 2, award in order of arrival, no reputation.
"""

import secrets
from dataclasses import asdict, dataclass, field

from ..behaviours.contract_net import Offer, assign, best_ambulance, offer_score
from ..behaviours.verification import (Belief, SourceView, case_priority, evidence_weight, os4_branch,
                                       should_declare, triage_incoherent)
from ..protocol.messages import (AEDRelease, AEDReservation, AEDReservationCancel, AEDReservationRefusal,
                                 AEDReservationRequest, AlertAck, AlertCancel, AlertReport, AmbulanceAward,
                                 AmbulanceCall, AmbulanceConfirmation, AmbulanceFailure, AmbulanceProposal,
                                 AmbulanceRefusal, AmbulanceRejection, Award, AwardConfirmation, AwardFailure,
                                 AwardRejection, CallForProposals, CancelAck, CandidateMerge, CandidateNotice,
                                 CaseClosure, CaseSnapshot, CorroborationQuery, CorroborationRefusal,
                                 CorroborationReply, Declaration, Disclosure, DisclosureRefusal, DisclosureRequest,
                                 GuidanceAck, GuidanceActivation, HelpEnRoute, OnSceneRoster, OutcomeLabels,
                                 Proposal, ProposalRefusal, Release, ReleaseAck, Retraction, StatusReport, Takeover,
                                 TriageAnswer, TriageQuestion)
from ..protocol.ontology import (ON_SCENE_STATUSES, Answer, CancelReason, CaseState, DisclosureField, EventType,
                                 Outcome, Priority, PromptStatus, Qualification, ResponderStatus, SourceKind,
                                 TaskType, TriageQuestionId, Verdict)
from ..sim.directory import Directory
from .base import Conversation, Incoming, Step

VERIFY, DISPATCH, TRACK, CLOSE, DISCARD = "VERIFY", "DISPATCH", "TRACK", "CLOSE", "DISCARD"
TRIAGE_QUESTIONS = (TriageQuestionId.SCENE_SAFE, TriageQuestionId.RESPONSIVE,
                    TriageQuestionId.BREATHING_NORMALLY, TriageQuestionId.CALLED_112)
FAILURE_STATUSES = {ResponderStatus.AED_MISSING, ResponderStatus.WITHDRAWN, ResponderStatus.UNSAFE_SCENE}


@dataclass
class AwardInfo:
    task: str
    eta_s: float
    aed_id: int | None = None
    status: str = "awarded"          # awarded | committed | failed | released
    arrive_by: float = 0.0
    on_scene_t: float | None = None
    late: bool = False
    aed_delivered: bool = False

    @property
    def active(self) -> bool:
        return self.status in ("awarded", "committed")


@dataclass
class CaseRecord:
    """Resource incidentCase[c] (analysis §4.1). Owned exclusively by one hub at a time (OS1)."""
    case_id: str
    cell: int
    t_open: float
    belief: Belief
    state: str = CaseState.VERIFYING
    priority: str = Priority.P3
    os4_rule: str | None = None
    needs: dict = field(default_factory=dict)
    alerts: dict = field(default_factory=dict)              # alert id -> source
    alert_reports: dict = field(default_factory=dict)       # alert id -> last AlertReport (for P26 merges)
    sources: dict = field(default_factory=dict)             # source -> SourceView
    queried: set = field(default_factory=set)
    triaged: set = field(default_factory=set)
    guides_asked: set = field(default_factory=set)
    guides: set = field(default_factory=set)                # witness devices running guidance
    subject: str | None = None                              # guardian to ask for the location (P24)
    location: list | None = None
    location_refused: bool = False
    invited: set = field(default_factory=set)
    proposals: dict = field(default_factory=dict)           # volunteer -> Proposal (arrival order)
    refusals: set = field(default_factory=set)
    awards: dict = field(default_factory=dict)              # volunteer -> AwardInfo
    call_deadline: float | None = None                      # pending re-recruitment call (OL6)
    call_tasks: dict = field(default_factory=dict)
    failed_aeds: set = field(default_factory=set)
    ems_invited: set = field(default_factory=set)
    ems_proposals: dict = field(default_factory=dict)
    ems_refusals: set = field(default_factory=set)
    ems: str | None = None
    ems_confirmed: bool = False
    ems_retry_at: float | None = None
    ems_retry_delay: float = 0.0                            # exponential backoff while no unit is free
    ems_took_over: bool = False
    reservation: dict | None = None                         # {aed_id, ref, token}
    reservation_pending: bool = False
    status: dict = field(default_factory=dict)              # responder -> last status
    clinical: dict | None = None
    released: bool = False
    retracted: bool = False
    human_false_alarm: bool = False
    silent_reinforced: bool = False
    recruit_exhausted: bool = False                         # nobody left to call
    triage_retry_at: dict = field(default_factory=dict)     # witness -> when to re-ask unanswered questions (F5)
    triage_retries: dict = field(default_factory=dict)
    triage_rechecked: set = field(default_factory=set)      # witnesses re-asked after an incoherent triage (F4)
    pending_release: dict = field(default_factory=dict)     # responder -> (time sent, reason, retries) until ReleaseAck
    location_requests: int = 0
    location_requested_at: float = 0.0
    outcome: str | None = None
    merged_into: tuple | None = None                        # (keeper hub, keeper case) after P26
    taken_over_from: str | None = None


class CaseFSM(Conversation):
    def __init__(self, hub, case_id: str, cell: int, first_event_type: str, record: CaseRecord | None = None):
        threads = {case_id} | (set(record.alerts) if record else set())
        super().__init__(threads)
        self.hub = hub
        v = hub.cfg["verification"]
        self.naive = hub.cfg["policy"]["allocation"] == "naive"
        self.case = record or CaseRecord(case_id, cell, hub.now(), Belief(v["prior"]))
        provisional = EventType(first_event_type).provisional_priority if first_event_type else Priority.P1
        self.deadline = self.case.t_open + v["w_max_s"][str(provisional)]
        self.announced = False
        restored = record is not None
        self.add_state(VERIFY, Verify(self), initial=not restored)
        self.add_state(DISPATCH, Dispatch(self))
        self.add_state(TRACK, Track(self), initial=restored)
        self.add_state(CLOSE, Close(self))
        self.add_state(DISCARD, Discard(self))
        for src, dst in ((VERIFY, DISPATCH), (VERIFY, DISCARD), (DISPATCH, TRACK), (DISPATCH, CLOSE),
                         (TRACK, CLOSE)):
            self.add_transition(src, dst)

    # --- takeover (P27 snapshot -> new owner) ---------------------------------------------------
    def snapshot(self, closed: bool = False) -> CaseSnapshot:
        c = self.case
        return CaseSnapshot(c.case_id, str(c.state), str(c.priority), c.cell, c.t_open, c.subject, c.ems,
                            {v: asdict(a) for v, a in c.awards.items()}, sorted(c.guides),
                            sorted(s.name for s in c.sources.values() if s.positive),
                            {k: c.reservation[k] for k in ("aed_id", "ref", "token")} if c.reservation else None,
                            closed)

    @classmethod
    def from_snapshot(cls, hub, snap: CaseSnapshot, previous_owner: str) -> "CaseFSM":
        v = hub.cfg["verification"]
        record = CaseRecord(snap.case_id, snap.cell, snap.t_open, Belief(v["prior"]), state=CaseState.TRACKING,
                            priority=snap.priority, subject=snap.subject, ems=snap.ems, ems_confirmed=bool(snap.ems),
                            awards={name: AwardInfo(**info) for name, info in snap.awards.items()},
                            guides=set(snap.guides), reservation=snap.reservation,
                            needs=dict(hub.cfg["dispatch"]["redundancy"][str(snap.priority)]),
                            taken_over_from=previous_owner)
        for name in snap.sources:
            kind = SourceKind.SENSOR if Directory.kind_of(name) == "device" else SourceKind.WITNESS
            record.sources[name] = SourceView(name, kind, hub.trust.trust(name), positive=True)
        if not snap.ems:
            record.ems_retry_at = hub.now()
        return cls(hub, snap.case_id, snap.cell, "", record)

    # --- helpers --------------------------------------------------------------------------------
    @property
    def vcfg(self) -> dict:
        return self.hub.cfg["verification"]

    @property
    def dcfg(self) -> dict:
        return self.hub.cfg["dispatch"]

    @property
    def declared(self) -> bool:
        return self.case.state not in (CaseState.VERIFYING, CaseState.DISCARDED)

    async def send(self, to: str, payload, performative=None) -> bool:
        return await self.hub.send_to(to, payload, thread=self.case.case_id, performative=performative)

    def log(self, kind: str, **fields) -> None:
        self.hub.log(kind, case=self.case.case_id, **fields)

    def source(self, name: str) -> SourceView:
        src = self.case.sources.get(name)
        if src is None:
            kind = SourceKind.SENSOR if Directory.kind_of(name) == "device" else SourceKind.WITNESS
            src = SourceView(name, kind, self.hub.trust.trust(name))
            self.case.sources[name] = src
        return src

    def add_evidence(self, src: SourceView, kind: str, confidence: float = 1.0) -> None:
        lr = self.vcfg["likelihood_ratio"][kind]
        weight = evidence_weight(src.trust, self.vcfg["trust_prior"])
        delta = self.case.belief.add(src.name, kind, lr, confidence, weight)
        self.log("evidence", source=src.name, evidence=kind, confidence=round(confidence, 3),
                 weight=round(weight, 3), delta=round(delta, 3), p=round(self.case.belief.probability, 4))

    async def replicate(self, closed: bool = False) -> None:
        if self.declared or closed:
            await self.hub.replicate(self.snapshot(closed))

    # --- message handling shared by all states -------------------------------------------------
    async def handle(self, inc: Incoming) -> None:
        p = inc.payload
        case = self.case
        if isinstance(p, AlertReport):
            await self.on_alert(p.origin or inc.sender, p)
        elif isinstance(p, AlertCancel):
            await self.on_cancel(p.origin or inc.sender, p)
        elif isinstance(p, CandidateMerge):
            for item in p.alerts:
                await self.on_alert(item["origin"], AlertReport(**item["report"]))
            self.log("candidate_absorbed", dropped=p.candidate_id, by=inc.sender, alerts=len(p.alerts))
        elif isinstance(p, CandidateNotice):
            case.merged_into = (inc.sender, p.candidate_id)            # set by the hub's P26 decision
        elif isinstance(p, CorroborationReply):
            await self.on_corroboration(inc, p)
        elif isinstance(p, CorroborationRefusal):
            self.log("corroboration_refused", source=inc.sender, reason=p.reason)
        elif isinstance(p, TriageAnswer):
            await self.on_triage(inc, p)
        elif isinstance(p, GuidanceAck):
            if p.accepted:
                case.guides.add(inc.sender)
                self.log("guidance_active", guide=inc.sender)
        elif isinstance(p, Disclosure):
            if p.field_name == DisclosureField.PRECISE_LOCATION:
                case.location = list(p.value)
                self.log("case_located", location=case.location, by=inc.sender)
        elif isinstance(p, DisclosureRefusal):
            case.location_refused = True
            self.log("disclosure_refused", field=p.field_name, reason=p.reason)
        elif isinstance(p, Proposal):
            case.proposals[inc.sender] = p
            case.refusals.discard(inc.sender)
        elif isinstance(p, ProposalRefusal):
            case.refusals.add(inc.sender)
        elif isinstance(p, AwardConfirmation):
            if inc.sender in case.awards and case.awards[inc.sender].status == "awarded":
                case.awards[inc.sender].status = "committed"
        elif isinstance(p, AwardFailure):
            await self.on_award_failure(inc.sender)
        elif isinstance(p, AmbulanceProposal):
            case.ems_proposals[inc.sender] = p.eta_s
        elif isinstance(p, AmbulanceRefusal):
            case.ems_refusals.add(inc.sender)
        elif isinstance(p, AmbulanceConfirmation):
            if inc.sender == case.ems:
                case.ems_confirmed = True
        elif isinstance(p, AmbulanceFailure):
            if inc.sender == case.ems:
                self.log("ambulance_failed", unit=inc.sender, reason=p.reason)
                case.ems, case.ems_confirmed = None, False
                case.ems_retry_at = self.hub.now()
        elif isinstance(p, AEDReservation):
            if case.reservation is not None:
                case.reservation = {"aed_id": p.aed_id, "ref": p.reservation_ref, "token": case.reservation["token"]}
            case.reservation_pending = False
        elif isinstance(p, AEDReservationRefusal):
            self.log("aed_reservation_refused", aed=p.aed_id, reason=p.reason)
            case.reservation = None
            case.reservation_pending = False
        elif isinstance(p, StatusReport):
            await self.on_status(inc, p)
        elif isinstance(p, ReleaseAck):
            case.pending_release.pop(inc.sender, None)
        else:
            self.log("unexpected", msg_type=type(p).__name__, sender=inc.sender)

    async def on_alert(self, origin: str, report: AlertReport) -> None:
        case = self.case
        src = self.source(origin)
        case.alert_reports[report.alert_id] = (origin, asdict(report))
        if report.alert_id not in case.alerts:
            case.alerts[report.alert_id] = origin
            self.hub.claim(report.alert_id, self)
            await self.hub.send_to(origin, AlertAck(report.alert_id, case.case_id), thread=report.alert_id)
            src.positive = True
            src.event_type = report.event_type
            kind = "witness_report" if src.kind == SourceKind.WITNESS else "sensor_alert"
            self.add_evidence(src, kind, report.confidence)
            # The data subject's guardian (P24): the patient's own device if one alerted, else the first witness.
            if case.subject is None or (src.kind == SourceKind.SENSOR and Directory.kind_of(case.subject) != "device"):
                case.subject = origin
            if src.kind == SourceKind.WITNESS and not self.naive:
                await self.ask_triage(origin)
        if report.prompt_status == PromptStatus.NO_RESPONSE and not src.wearer_no_response:
            src.wearer_no_response = True
            self.add_evidence(src, "wearer_no_response")

    async def on_cancel(self, origin: str, cancel: AlertCancel) -> None:
        src = self.case.sources.get(origin)
        await self.hub.send_to(origin, CancelAck(cancel.alert_id, str(self.case.state)), thread=cancel.alert_id)
        if src is None or src.cancelled:
            return
        src.cancelled = True
        self.add_evidence(src, "wearer_ok" if cancel.reason == CancelReason.WEARER_OK else "witness_retracts")
        if self.declared and self.case.outcome is None and self.case.belief.probability < self.vcfg["retract_below"]:
            await self.retract(f"{cancel.reason} from {origin}", human_confirmed=True)

    async def on_corroboration(self, inc: Incoming, reply: CorroborationReply) -> None:
        if reply.verdict == Verdict.NO_DATA:
            return
        src = self.source(inc.sender)
        if reply.verdict == Verdict.CONFIRM:
            if not src.positive:
                src.positive = True
                self.add_evidence(src, "corroboration_confirm", reply.confidence)
            if src.kind == SourceKind.WITNESS:
                await self.ask_triage(inc.sender)
        elif reply.verdict == Verdict.DENY:
            self.add_evidence(src, "corroboration_deny", reply.confidence)

    async def on_triage(self, inc: Incoming, answer: TriageAnswer) -> None:
        src = self.source(inc.sender)
        src.triage[answer.question] = answer.answer
        self.log("triage_answer", source=inc.sender, question=answer.question, answer=answer.answer)
        if src.triage_complete and not src.triage_scored:
            src.triage_scored = True
            if triage_incoherent(src.triage):                                    # F4
                if inc.sender not in self.case.triage_rechecked:
                    # Observation errors are independent: ask the two key questions once more.
                    self.case.triage_rechecked.add(inc.sender)
                    for q in (TriageQuestionId.RESPONSIVE, TriageQuestionId.BREATHING_NORMALLY):
                        src.triage.pop(q, None)
                    src.triage_scored = False
                    self.case.triage_retries.pop(inc.sender, None)
                    await self.send_triage(inc.sender, (TriageQuestionId.RESPONSIVE,
                                                        TriageQuestionId.BREATHING_NORMALLY))
                    self.log("triage_incoherent", source=inc.sender, action="re-ask")
                else:
                    self.log("triage_incoherent", source=inc.sender, action="ignored")
                return
            responsive = src.triage[TriageQuestionId.RESPONSIVE]
            breathing = src.triage[TriageQuestionId.BREATHING_NORMALLY]
            if responsive == Answer.NO:
                self.add_evidence(src, "triage_p1" if breathing == Answer.NO else "triage_p2")
                await self.activate_guidance(inc.sender, src.triage)

    async def ask_triage(self, witness: str) -> None:
        if witness in self.case.triaged:
            return
        self.case.triaged.add(witness)
        await self.send_triage(witness, TRIAGE_QUESTIONS)

    async def send_triage(self, witness: str, questions) -> None:
        reply_by = self.hub.now() + self.vcfg["triage_deadline_s"]
        for question in questions:
            await self.send(witness, TriageQuestion(self.case.case_id, str(question), reply_by))
        self.case.triage_retry_at[witness] = reply_by

    async def retry_triage(self) -> None:
        """F5: re-ask the questions a witness has not answered by the deadline (answers are idempotent)."""
        now = self.hub.now()
        for witness, at in list(self.case.triage_retry_at.items()):
            if now < at:
                continue
            src = self.case.sources.get(witness)
            missing = [q for q in TRIAGE_QUESTIONS if src is None or q not in src.triage]
            tries = self.case.triage_retries.get(witness, 0)
            if not missing or tries >= self.vcfg["max_retries"]:
                del self.case.triage_retry_at[witness]
                continue
            self.case.triage_retries[witness] = tries + 1
            self.log("triage_retry", witness=witness, questions=[str(q) for q in missing])
            await self.send_triage(witness, missing)

    async def activate_guidance(self, witness: str, triage: dict) -> None:
        """OL3: guidance starts with the triage, before the declaration; OL5: only triaged witnesses."""
        if witness in self.case.guides_asked or self.case.outcome is not None:
            return
        self.case.guides_asked.add(witness)
        priority = case_priority(list(self.case.sources.values()))
        await self.send(witness, GuidanceActivation(self.case.case_id, str(priority), dict(triage)))

    async def on_status(self, inc: Incoming, report: StatusReport) -> None:
        case = self.case
        case.status[inc.sender] = report.status
        self.log("status", source=inc.sender, status=report.status, eta=report.eta_s)
        info = case.awards.get(inc.sender)
        if info is not None:
            if report.status == ResponderStatus.EN_ROUTE and report.eta_s is not None and info.active:
                # The responder's own ETA for the current leg refines the award-time estimate (_MonitorProgress).
                info.arrive_by = self.hub.now() + report.eta_s + self.dcfg["eta_slack_s"]
                info.late = False
            if report.status in ON_SCENE_STATUSES and info.on_scene_t is None:
                info.on_scene_t = self.hub.now()
            if report.status == ResponderStatus.AED_DELIVERED:
                info.aed_delivered = True
            if report.status in ON_SCENE_STATUSES:
                await self.release_surplus()                                   # OL8
            if report.status in FAILURE_STATUSES and info.active:              # OL6
                info.status = "failed"
                if report.status == ResponderStatus.AED_MISSING and info.aed_id is not None:
                    case.failed_aeds.add(info.aed_id)
                    case.reservation = None
                self.log("award_failed", responder=inc.sender, task=info.task, reason=report.status)
                await self.replicate()
            return
        if inc.sender in case.guides and report.status == ResponderStatus.WITNESS_SILENT:
            if case.priority == Priority.P1 and not case.silent_reinforced and not self.anyone_on_scene():
                case.silent_reinforced = True                                  # F11: reinforce volunteers
                case.needs[TaskType.GO_TO_PATIENT] = case.needs.get(TaskType.GO_TO_PATIENT, 0) + 1
            return
        if inc.sender != case.ems:
            return
        if report.status == ResponderStatus.ON_SCENE:
            on_scene = [v for v, a in case.awards.items() if a.on_scene_t is not None and a.active]
            await self.send(inc.sender, OnSceneRoster(case.case_id, on_scene or sorted(case.guides)))
        elif report.status == ResponderStatus.EMS_TOOK_OVER:
            case.ems_took_over = True
            await self.release_all("ems_took_over")                       # OL7
        elif report.status == ResponderStatus.CLINICAL_CONFIRMATION:
            case.clinical = dict(report.detail)
            if not case.clinical.get("real_incident", True):
                await self.release_all("false_alarm")
                case.outcome = Outcome.FALSE_ALARM
        elif report.status == ResponderStatus.TRANSPORTING:
            case.outcome = Outcome.TRANSPORTED

    def anyone_on_scene(self) -> bool:
        return any(a.on_scene_t is not None and a.active for a in self.case.awards.values())

    # --- dispatch helpers ---------------------------------------------------------------------
    async def request_location(self) -> None:
        if self.case.subject is None:
            self.log("no_subject")
            return
        self.case.location_requests += 1
        self.case.location_requested_at = self.hub.now()
        await self.send(self.case.subject, DisclosureRequest(
            self.case.case_id, DisclosureField.PRECISE_LOCATION, "dispatch", str(self.case.priority),
            recipients=["awarded responders", "EMS unit"]))

    async def call_ambulance(self) -> float:
        case = self.case
        reply_by = self.hub.now() + self.dcfg["ambulance_deadline_s"]
        case.ems_proposals.clear()
        case.ems_refusals.clear()
        case.ems_invited = set(self.hub.ctx.directory.ems_names)
        for unit in sorted(case.ems_invited):
            await self.send(unit, AmbulanceCall(case.case_id, str(case.priority), case.cell, reply_by))
        self.log("ambulance_requested", units=len(case.ems_invited))
        return reply_by

    async def award_ambulance(self) -> None:
        case = self.case
        ranked = best_ambulance(case.ems_proposals)
        if not ranked or case.location is None:
            base = self.dcfg["ambulance_retry_s"]
            case.ems_retry_delay = min(4 * base, 2 * case.ems_retry_delay) if case.ems_retry_delay else base
            self.log("no_ambulance", proposals=len(ranked), located=case.location is not None,
                     retry_in=case.ems_retry_delay)
            case.ems_retry_at = self.hub.now() + case.ems_retry_delay
            return
        case.ems = ranked[0]
        case.ems_retry_at = None
        await self.send(case.ems, AmbulanceAward(case.case_id, str(case.priority), case.location))
        for unit in ranked[1:]:
            await self.send(unit, AmbulanceRejection(case.case_id))
        self.log("ems_award", unit=case.ems, eta=round(case.ems_proposals[case.ems], 1))
        await self.replicate()

    async def call_responders(self, ring: int, tasks: dict) -> float | None:
        """P08 to registered volunteers up to `ring` not called before; None if there is nobody left."""
        case = self.case
        targets = [v for v in self.hub.registered("volunteer", ring) if v not in case.invited]
        if not targets:
            self.log("responders_called", ring=ring, invited=0, tasks={str(t): n for t, n in tasks.items()})
            return None
        reply_by = self.hub.now() + self.dcfg["proposal_deadline_s"]
        centre = self.hub.world.grid.centroid(case.cell)
        aeds = [{"aed_id": a, "pos": list(self.hub.world.aed_registry[a]["pos"])}
                for a in self.hub.world.aeds_near(centre, self.dcfg["candidate_aeds"] + len(case.failed_aeds))
                if a not in case.failed_aeds][:self.dcfg["candidate_aeds"]]
        cfp = CallForProposals(case.case_id, {str(t): n for t, n in tasks.items()}, case.cell, str(case.priority),
                               Qualification.BLS, reply_by, aeds if TaskType.FETCH_AED in tasks else [])
        for volunteer in targets:
            await self.send(volunteer, cfp)
        case.invited.update(targets)
        self.log("responders_called", ring=ring, invited=len(targets), tasks={str(t): n for t, n in tasks.items()})
        return reply_by

    def offers(self, exclude=()) -> list[Offer]:
        result = []
        for bidder, proposal in self.case.proposals.items():
            if bidder in exclude:
                continue
            trust = self.hub.trust.trust(bidder)
            for o in proposal.offers:
                if o["task"] == TaskType.FETCH_AED and o.get("aed_id") in self.case.failed_aeds:
                    continue
                result.append(Offer(bidder, o["task"], float(o["eta_s"]), proposal.qualification, trust,
                                    o.get("aed_id")))
        return result

    def score(self, offer: Offer) -> float:
        return offer_score(offer, Qualification.BLS, self.dcfg["quality_penalty"],
                           self.vcfg["trust_prior"], self.dcfg["trust_exponent"])

    async def reserve_aed(self, aed_id: int) -> bool:
        case = self.case
        token = secrets.token_hex(6)
        case.reservation = {"aed_id": aed_id, "ref": None, "token": token}
        case.reservation_pending = True
        await self.send(Directory.hub(aed_id), AEDReservationRequest(
            case.case_id, aed_id, self.hub.cfg["aed"]["reservation_valid_s"], str(case.priority), token))
        until = self.hub.now() + self.dcfg["reservation_timeout_s"]
        while case.reservation_pending and self.hub.now() < until:
            inc = await self.next_incoming(until)
            if inc is not None:
                await self.handle(inc)
        if case.reservation_pending:                 # no answer (custodian down?): give up on this AED
            case.reservation_pending = False
            case.reservation = None
            case.failed_aeds.add(aed_id)
        return case.reservation is not None and case.reservation.get("ref") is not None

    async def send_award(self, offer: Offer) -> None:
        case = self.case
        arrive_by = self.hub.now() + offer.eta_s + self.dcfg["eta_slack_s"]
        res = case.reservation if offer.task == TaskType.FETCH_AED else None
        guide = sorted(case.guides)[0] if case.guides else None
        await self.send(offer.bidder, Award(case.case_id, offer.task, case.location, arrive_by,
                                            res["aed_id"] if res else None, res["ref"] if res else None,
                                            res["token"] if res else None, guide=guide))
        case.awards[offer.bidder] = AwardInfo(offer.task, offer.eta_s, res["aed_id"] if res else None,
                                              arrive_by=arrive_by)
        self.log("award", responder=offer.bidder, task=offer.task, eta=round(offer.eta_s, 1),
                 aed=res["aed_id"] if res else None, qualification=case.proposals[offer.bidder].qualification)

    def uncovered(self) -> dict:
        """Tasks still needed: awards that failed, or are late without having arrived, do not cover (OL6)."""
        case = self.case
        missing = {}
        for task, wanted in case.needs.items():
            covering = [a for a in case.awards.values() if a.task == task and a.active
                        and (a.on_scene_t is not None or not a.late)]
            if task == TaskType.FETCH_AED and any(a.aed_delivered for a in case.awards.values()):
                continue
            if wanted - len(covering) > 0:
                missing[task] = wanted - len(covering)
        return missing

    async def award_open_slots(self) -> None:
        """Award the uncovered tasks from the proposals received so far (Contract Net, D4)."""
        case = self.case
        missing = self.uncovered()
        if not missing or case.location is None:
            return
        taken = set(case.awards)
        if missing.get(TaskType.FETCH_AED):
            fetch = sorted((o for o in self.offers(exclude=taken) if o.task == TaskType.FETCH_AED and o.aed_id is not None),
                           key=self.score)
            for offer in fetch:
                res = case.reservation
                if res and res.get("ref") and res["aed_id"] == offer.aed_id:
                    reserved = True                                  # reuse the case's reservation
                else:
                    if res and res.get("ref"):                       # do not leak a reservation of another AED
                        await self.send(Directory.hub(res["aed_id"]),
                                        AEDReservationCancel(case.case_id, res["aed_id"], res["ref"]))
                    reserved = await self.reserve_aed(offer.aed_id)
                if reserved:
                    await self.send_award(offer)
                    taken.add(offer.bidder)
                    break
        remaining = {t: n for t, n in missing.items() if t != TaskType.FETCH_AED}
        n_left = self.dcfg["n_max"] - sum(1 for a in case.awards.values() if a.active)
        for offer in assign(self.offers(exclude=taken), remaining, n_left, self.score):
            await self.send_award(offer)

    async def award_in_arrival_order(self) -> None:
        """Baseline B1: the first volunteers to accept get the open tasks."""
        case = self.case
        if case.location is None:
            return
        for bidder, proposal in list(case.proposals.items()):
            if bidder in case.awards:
                continue
            missing = self.uncovered()
            if not missing:
                return
            for o in proposal.offers:
                if missing.get(o["task"]):
                    if o["task"] == TaskType.FETCH_AED and not await self.reserve_aed(o["aed_id"]):
                        continue
                    await self.send_award(Offer(bidder, o["task"], float(o["eta_s"]), proposal.qualification,
                                                0.5, o.get("aed_id")))
                    break

    async def reject_losers(self) -> None:
        for bidder in self.case.proposals:
            if bidder not in self.case.awards:
                await self.send(bidder, AwardRejection(self.case.case_id))

    async def on_award_failure(self, volunteer: str) -> None:
        """The volunteer became busy after bidding: its task goes to the next best bidder."""
        info = self.case.awards.get(volunteer)
        if info is None or not info.active:
            return
        info.status = "failed"
        self.log("award_failed", responder=volunteer, task=info.task, reason="busy")
        if self.naive:
            await self.award_in_arrival_order()
        else:
            await self.award_open_slots()

    async def check_progress(self) -> None:
        """_MonitorProgress: flag late awards (ETA + δ) and re-recruit uncovered tasks (OL6)."""
        case = self.case
        now = self.hub.now()
        if case.outcome is not None or case.ems_took_over or case.retracted:
            return
        for name, info in case.awards.items():
            if info.active and info.on_scene_t is None and not info.late and now > info.arrive_by:
                info.late = True
                self.log("award_at_risk", responder=name, task=info.task)
        missing = self.uncovered()
        if missing and case.call_deadline is None and case.location is not None and not case.recruit_exhausted:
            if self.offers(exclude=set(case.awards)):
                await self.award_open_slots()
                missing = self.uncovered()
            if missing:
                case.call_tasks = missing
                case.call_deadline = await self.call_responders(2, missing)
                case.recruit_exhausted = case.call_deadline is None
                self.log("recruit", tasks={str(t): n for t, n in missing.items()}, exhausted=case.recruit_exhausted)

    async def release_surplus(self) -> None:
        """OL8: once N_need rescuers are on scene, release those still on the way (except an AED not yet delivered)."""
        case = self.case
        n_need = self.dcfg["n_need"].get(str(case.priority), 1)
        if sum(1 for a in case.awards.values() if a.on_scene_t is not None and a.active) < n_need:
            return
        aed_done = any(a.aed_delivered for a in case.awards.values())
        for name, info in case.awards.items():
            if info.active and info.on_scene_t is None and (info.task != TaskType.FETCH_AED or aed_done):
                info.status = "released"
                await self.send_release(name, "enough_on_scene")
        if case.call_deadline is not None:
            case.call_deadline = None

    async def send_help_notice(self) -> None:
        """P15: tell the guides on scene what help is on the way (ETAs only, no identities)."""
        case = self.case
        if not case.guides:
            return
        now = self.hub.now()
        go = [a.arrive_by - self.dcfg["eta_slack_s"] - now for a in case.awards.values()
              if a.active and a.task == TaskType.GO_TO_PATIENT]
        aed = [a.arrive_by - self.dcfg["eta_slack_s"] - now for a in case.awards.values()
               if a.active and a.task == TaskType.FETCH_AED]
        ems = case.ems_proposals.get(case.ems) if case.ems else None
        notice = HelpEnRoute(case.case_id, round(min(go), 1) if go else None, round(min(aed), 1) if aed else None,
                             ems)
        for guide in sorted(case.guides):
            await self.send(guide, notice)

    async def retract(self, reason: str, human_confirmed: bool) -> None:
        """P07: undo a declaration. The ambulance is cancelled only for a human-confirmed false alarm (OS6)."""
        case = self.case
        if case.retracted:
            return
        case.retracted = True
        case.human_false_alarm = human_confirmed
        self.hub.log_local(Retraction(case.case_id, reason, round(case.belief.probability, 4)),
                           "IncidentCoordinator", case.case_id)
        self.log("case_retracted", reason=reason, human_confirmed=human_confirmed,
                 p=round(case.belief.probability, 4))
        await self.release_all("false_alarm")
        if human_confirmed:
            if case.ems:
                await self.send_release(case.ems, "false_alarm")
            case.outcome = Outcome.FALSE_ALARM

    async def send_release(self, name: str, reason: str, retries: int = 0) -> None:
        await self.send(name, Release(self.case.case_id, reason))
        self.case.pending_release[name] = (self.hub.now(), reason, retries)
        self.log("release", responder=name, reason=reason, retry=retries)

    async def ensure_location(self) -> None:
        """F5: keep asking for the location while unknown (e.g. the answer to P24 was lost after a takeover)."""
        case = self.case
        if (case.location is None and not case.location_refused and case.subject
                and case.location_requests <= self.vcfg["max_retries"]
                and self.hub.now() - case.location_requested_at >= self.vcfg["retry_after_s"]):
            await self.request_location()

    async def retry_releases(self) -> None:
        """F5: P14 is acknowledged; resend a release that got no ReleaseAck."""
        now = self.hub.now()
        for name, (t, reason, retries) in list(self.case.pending_release.items()):
            if now - t >= self.vcfg["retry_after_s"]:
                if retries >= self.vcfg["max_retries"]:
                    del self.case.pending_release[name]
                else:
                    await self.send_release(name, reason, retries + 1)

    async def release_all(self, reason: str) -> None:
        case = self.case
        if case.released:
            return
        case.released = True
        case.call_deadline = None
        for volunteer, info in case.awards.items():
            if info.active:
                info.status = "released"
                await self.send_release(volunteer, reason)
        res = case.reservation
        if res and res.get("ref") and not any(a.aed_delivered or case.status.get(v) == ResponderStatus.AED_OK
                                              for v, a in case.awards.items()):
            await self.send(Directory.hub(res["aed_id"]), AEDReservationCancel(case.case_id, res["aed_id"], res["ref"]))
            case.reservation = None
        await self.replicate()

    def outcome_labels(self) -> list[dict]:
        """P21: reputation labels. The EMS clinical confirmation is the reference; a false alarm confirmed
        by a human (wearer or witness) also counts. Responders are judged on arriving within ETA + δ."""
        case = self.case
        if case.clinical is not None:
            real = bool(case.clinical.get("real_incident"))
        elif case.human_false_alarm:
            real = False
        else:
            real = None
        labels = []
        if real is not None:
            for src in case.sources.values():
                if src.positive:
                    labels.append({"pseudonym": src.name, "kind": "source", "success": real})
        for name, info in case.awards.items():
            if info.on_scene_t is not None:
                labels.append({"pseudonym": name, "kind": "responder", "success": info.on_scene_t <= info.arrive_by})
            elif info.status == "failed" or info.late:
                labels.append({"pseudonym": name, "kind": "responder", "success": False})
        return labels

    async def finished(self) -> None:
        self.hub.case_finished(self)


# --- states ------------------------------------------------------------------------------------
class Verify(Step):
    async def step(self):
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        sent_queries = False
        while True:
            wake = min([fsm.deadline] + list(case.triage_retry_at.values()))
            inc = await fsm.next_incoming(max(wake, hub.now() + 0.2))
            if inc is not None:
                await fsm.handle(inc)
            if case.sources and not fsm.announced:
                fsm.announced = True
                await hub.announce_candidate(fsm)                              # P26
            if case.merged_into is not None:
                await hub.drop_duplicate(fsm)
                fsm.log("candidate_discarded", p=round(case.belief.probability, 4), priority=str(case.priority),
                        reason="merged", keeper=case.merged_into[1])
                self.set_next_state(DISCARD)
                return
            if fsm.naive and case.sources:
                await self.declare(case_priority(list(case.sources.values())), "naive")
                return
            if not sent_queries and case.sources:
                sent_queries = True
                await self.query_neighbourhood()
            await fsm.retry_triage()
            priority = case_priority(list(case.sources.values()))
            rule = os4_branch(list(case.sources.values()), fsm.vcfg["human_reliable_min_trust"])
            p = case.belief.probability
            if should_declare(p, priority, fsm.vcfg["tau_declare"], rule):
                await self.declare(priority, rule)
                return
            if p < fsm.vcfg["discard_below"] or hub.now() >= fsm.deadline:
                fsm.log("candidate_discarded", p=round(p, 4), priority=str(priority),
                        reason="belief_too_low" if p < fsm.vcfg["discard_below"] else "window_expired")
                self.set_next_state(DISCARD)
                return

    async def declare(self, priority, rule):
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        case.priority, case.os4_rule, case.state = priority, rule, CaseState.DECLARED
        p = case.belief.probability
        fsm.log("case_declared", priority=str(priority), p=round(p, 4), rule=rule, cell=case.cell,
                sources=sorted(s.name for s in case.sources.values() if s.positive and not s.cancelled),
                latency=round(hub.now() - case.t_open, 2))
        self.set_next_state(DISPATCH)

    async def query_neighbourhood(self):
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        reply_by = hub.now() + fsm.vcfg["corroboration_deadline_s"]
        query = CorroborationQuery(case.case_id, case.cell, case.t_open - fsm.vcfg["merge_window_s"],
                                   reply_by, reply_by)
        targets = [n for n in hub.registered("sensor", 1) + hub.registered("witness", 1) if n not in case.sources]
        for name in targets:
            await fsm.send(name, query)
            case.queried.add(name)
        fsm.log("corroboration_requested", targets=len(targets))


class Dispatch(Step):
    async def step(self):
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        case.state = CaseState.DISPATCHING
        hub.log_local(Declaration(case.case_id, str(case.priority), round(case.belief.probability, 4), case.cell,
                                  case.os4_rule or "", sorted(case.sources)), "IncidentCoordinator", case.case_id)
        if case.priority == Priority.P3:          # contact and guidance only (analysis §2.2)
            case.outcome = Outcome.RESOLVED_ON_SCENE
            self.set_next_state(CLOSE)
            return
        case.needs = dict(fsm.dcfg["redundancy"][str(case.priority)])
        await fsm.replicate()
        await fsm.request_location()
        ems_deadline = await fsm.call_ambulance()
        ring = 2 if fsm.naive else 1
        deadline = await fsm.call_responders(ring, case.needs)
        await self.collect(max(deadline or 0.0, ems_deadline))
        if not case.proposals and not fsm.naive and case.outcome is None:
            wider = await fsm.call_responders(2, case.needs)                 # widen to ring 2 (D3)
            if wider is not None:
                await self.collect(wider)
        if case.location is None and not case.location_refused:
            await fsm.request_location()                                   # F5: ask again once
            until = hub.now() + fsm.dcfg["location_wait_s"]
            while case.location is None and hub.now() < until:
                inc = await fsm.next_incoming(until)
                if inc is not None:
                    await fsm.handle(inc)
        if case.outcome is not None:              # retracted while dispatching
            self.set_next_state(CLOSE)
            return
        await fsm.award_ambulance()
        if fsm.naive:
            await fsm.award_in_arrival_order()
        else:
            await fsm.award_open_slots()
        await fsm.reject_losers()
        if case.location is None:
            fsm.log("no_location_for_awards")
        await fsm.send_help_notice()
        case.state = CaseState.TRACKING
        await fsm.replicate()
        self.set_next_state(TRACK)

    async def collect(self, deadline: float):
        """Gather proposals until the deadline, or until everyone invited has answered."""
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        while hub.now() < deadline and case.outcome is None:
            answered = case.invited <= (set(case.proposals) | case.refusals)
            ems_answered = case.ems_invited <= (set(case.ems_proposals) | case.ems_refusals)
            if answered and ems_answered and case.location is not None:
                return
            inc = await fsm.next_incoming(deadline)
            if inc is not None:
                await fsm.handle(inc)
                if fsm.naive and isinstance(inc.payload, Proposal):
                    await fsm.award_in_arrival_order()                       # B1: first come, first served


class Track(Step):
    async def step(self):
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        if case.taken_over_from is not None:
            await self.announce_takeover()
        timeout = case.t_open + fsm.dcfg["case_timeout_s"]
        award_ems_at = None
        while case.outcome is None:
            now = hub.now()
            if now >= timeout:
                case.outcome = Outcome.TIMEOUT
                break
            if case.ems is None and case.ems_retry_at is not None and now >= case.ems_retry_at \
                    and award_ems_at is None and not case.retracted:
                award_ems_at = await fsm.call_ambulance()
                case.ems_retry_at = None
            if award_ems_at is not None and (now >= award_ems_at or case.ems_invited <= (
                    set(case.ems_proposals) | case.ems_refusals)):
                award_ems_at = None
                await fsm.award_ambulance()
                await fsm.send_help_notice()
            if case.call_deadline is not None and now >= case.call_deadline:
                case.call_deadline = None
                if fsm.naive:
                    await fsm.award_in_arrival_order()
                else:
                    await fsm.award_open_slots()
                await fsm.reject_losers()
                await fsm.send_help_notice()
                await fsm.replicate()
            await fsm.ensure_location()
            await fsm.check_progress()
            await fsm.retry_releases()
            pending = [a.arrive_by for a in case.awards.values() if a.active and a.on_scene_t is None and not a.late]
            wake = min(t for t in (timeout, award_ems_at, case.ems_retry_at, case.call_deadline, now + 30,
                                   *pending) if t is not None)
            inc = await fsm.next_incoming(max(wake, now + 0.5))
            if inc is not None:
                await fsm.handle(inc)
        self.set_next_state(CLOSE)

    async def announce_takeover(self):
        """P28: tell every participant who coordinates the case now; ask again for the location (D7)."""
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        participants = {v for v, a in case.awards.items() if a.active} | set(case.guides) | (
            {case.ems} if case.ems else set())
        for name in sorted(participants):
            await fsm.send(name, Takeover(case.case_id, hub.label))
        fsm.log("case_taken_over", previous=case.taken_over_from, participants=len(participants))
        await fsm.request_location()


class Close(Step):
    async def step(self):
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        case.state = CaseState.CLOSED
        await fsm.release_all("case_closed")
        closure = CaseClosure(case.case_id, str(case.outcome), hub.now())
        recipients = {v for v in case.awards} | ({case.ems} if case.ems else set()) | (
            {case.subject} if case.subject else set()) | set(case.guides)
        for name in sorted(recipients):
            await fsm.send(name, closure)
        if case.subject:                          # the guardian purges on closure (OS11): send it twice
            await fsm.send(case.subject, closure)
        res = case.reservation
        if res and res.get("ref"):
            await fsm.send(Directory.hub(res["aed_id"]), AEDRelease(case.case_id, res["aed_id"], res["ref"]))
        fsm.log("case_closed", outcome=str(case.outcome), priority=str(case.priority),
                duration=round(hub.now() - case.t_open, 1))
        labels = fsm.outcome_labels()
        hub.log_local(OutcomeLabels(case.case_id, labels), "ReputationManager", case.case_id)     # P21 (OL9)
        hub.apply_outcome(case.case_id, labels)
        await fsm.replicate(closed=True)


class Discard(Step):
    async def step(self):
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        case.state = CaseState.DISCARDED
        if case.guides:                           # guidance was active: the verifier closes it
            for guide in sorted(case.guides):
                await fsm.send(guide, CaseClosure(case.case_id, Outcome.FALSE_ALARM, hub.now()))
        # A source that alerted and was then cancelled by a human (wearer "I'm fine", witness retracted)
        # gave a false alert: a weak negative label for its reputation.
        labels = [{"pseudonym": s.name, "kind": "source", "success": False, "weight": 0.5}
                  for s in case.sources.values() if s.positive and s.cancelled]
        if labels and case.merged_into is None:
            hub.log_local(OutcomeLabels(case.case_id, labels), "ReputationManager", case.case_id)
            hub.apply_outcome(case.case_id, labels)

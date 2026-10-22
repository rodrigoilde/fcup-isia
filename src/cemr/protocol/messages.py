"""Message payloads of protocols P01–P28 (the message schemas of the interaction model).

Each payload is a dataclass registered with its protocol and the FIPA performatives it may travel
with. The JSON body carries a "type" field naming the payload, so decoding does not depend on the
envelope. The envelope itself (sender, receiver, thread, performative, protocol, ontology,
language, seq) is built in agents/base.py.

Conventions:
- the sender's JID is its stable pseudonym (D7), so payloads never repeat it;
- positions are [x, y] in metres and appear only in messages allowed to carry them (OS5);
- times are simulated seconds since the start of the run.
"""

import json
from dataclasses import MISSING, asdict, dataclass, field, fields

from .ontology import Performative as Pf
from .ontology import Protocol as P

_REGISTRY: dict[str, type] = {}


def doc(text: str, default=MISSING, factory=MISSING):
    """Dataclass field with a description, used to generate the schema tables of docs/04."""
    if factory is not MISSING:
        return field(default_factory=factory, metadata={"doc": text})
    if default is not MISSING:
        return field(default=default, metadata={"doc": text})
    return field(metadata={"doc": text})


def payload(protocol: P, *performatives: Pf, local: bool = False):
    def register(cls):
        cls = dataclass(cls)
        cls.PROTOCOL = protocol
        cls.PERFORMATIVES = tuple(performatives)
        cls.LOCAL = local
        _REGISTRY[cls.__name__] = cls
        return cls
    return register


def encode(obj) -> str:
    data = asdict(obj)
    data["type"] = type(obj).__name__
    return json.dumps(data, separators=(",", ":"))


def decode(body: str):
    data = json.loads(body)
    cls = _REGISTRY[data.pop("type")]
    return cls(**data)


def all_payloads() -> list[type]:
    """All payload classes, by protocol and then in definition order (request before reply)."""
    return sorted(_REGISTRY.values(), key=lambda c: c.PROTOCOL.code)


def field_docs(cls) -> list[tuple[str, str, str]]:
    return [(f.name, getattr(f.type, "__name__", str(f.type)), f.metadata.get("doc", "")) for f in fields(cls)]


# --- P01 RaiseCandidateAlert ------------------------------------------------------------------
@payload(P.RAISE_CANDIDATE_ALERT, Pf.INFORM)
class AlertReport:
    """A suspected collapse, from a device (SensorMonitor) or a citizen (WitnessReporter).
    Re-sent on the same thread to update the wearer prompt status."""
    alert_id: str = doc("Unique per source; also the conversation thread")
    source_kind: str = doc("sensor | witness")
    event_type: str = doc("collapse_cardiac | fall_immobile | fall | witness_collapse")
    confidence: float = doc("Local confidence in [0, 1]")
    cell: int = doc("Coarse location: the cell id only (D7)")
    t_event: float = doc("When the event was detected or seen")
    policy: str = doc("alert_first | confirm_first | human")
    prompt_status: str = doc("Wearer prompt: pending | no_response | not_applicable")
    signal_quality: float = doc("Sensor signal quality in [0, 1] (1 for humans)", 1.0)
    origin: str | None = doc("Original source when a hub relays the alert after a merge (P26)", None)


@payload(P.RAISE_CANDIDATE_ALERT, Pf.INFORM)
class AlertAck:
    """The hub's receipt: the alert joined candidate `candidate_id`."""
    alert_id: str = doc("Alert being acknowledged")
    candidate_id: str = doc("Candidate (later case) the alert was merged into")


# --- P02 CancelAlert --------------------------------------------------------------------------
@payload(P.CANCEL_ALERT, Pf.CANCEL)
class AlertCancel:
    """The wearer answered "I'm fine", or the witness retracts the report."""
    alert_id: str = doc("Alert to cancel")
    reason: str = doc("wearer_ok | witness_retracts")
    t_event: float = doc("When the cancellation happened")
    origin: str | None = doc("Original source when relayed by a hub", None)


@payload(P.CANCEL_ALERT, Pf.INFORM)
class CancelAck:
    alert_id: str = doc("Cancelled alert")
    candidate_state: str = doc("State of the candidate after the cancellation")


# --- P03 CorroborationRequest -----------------------------------------------------------------
@payload(P.CORROBORATION_REQUEST, Pf.QUERY_REF)
class CorroborationQuery:
    """Ask nearby sources for independent evidence. Never includes the precise location or the
    patient's identity."""
    candidate_id: str = doc("Candidate under verification (thread)")
    cell: int = doc("Cell of the candidate")
    window_from: float = doc("Start of the time window of interest")
    window_to: float = doc("End of the time window of interest")
    reply_by: float = doc("Deadline; no answer counts as no_data")


@payload(P.CORROBORATION_REQUEST, Pf.INFORM)
class CorroborationReply:
    candidate_id: str = doc("Candidate being corroborated")
    verdict: str = doc("confirm | deny | no_data")
    confidence: float = doc("Confidence of the summarised evidence in [0, 1]")
    quality: float = doc("Signal or observation quality in [0, 1]", 1.0)


@payload(P.CORROBORATION_REQUEST, Pf.REFUSE)
class CorroborationRefusal:
    candidate_id: str = doc("Candidate being corroborated")
    reason: str = doc("e.g. consent: the owner's policy does not allow sharing")


# --- P04 TriageQuestionnaire ------------------------------------------------------------------
@payload(P.TRIAGE_QUESTIONNAIRE, Pf.QUERY_IF)
class TriageQuestion:
    """One question to a witness on scene, in the order of the BLS algorithm."""
    candidate_id: str = doc("Candidate under verification (thread)")
    question: str = doc("scene_safe | responsive | breathing_normally | called_112")
    reply_by: float = doc("Deadline for the answer")


@payload(P.TRIAGE_QUESTIONNAIRE, Pf.INFORM)
class TriageAnswer:
    candidate_id: str = doc("Candidate under verification")
    question: str = doc("Question being answered")
    answer: str = doc("yes | no | unknown (silence counts as unknown)")
    t_answer: float = doc("When the witness answered")


# --- P05 ActivateGuidance ---------------------------------------------------------------------
@payload(P.ACTIVATE_GUIDANCE, Pf.REQUEST)
class GuidanceActivation:
    """Start step-by-step BLS guidance on the witness's device, before verification ends."""
    candidate_id: str = doc("Candidate or case (thread)")
    priority: str = doc("Provisional priority")
    triage: dict = doc("Triage answers already obtained, so the guide does not repeat them", factory=dict)


@payload(P.ACTIVATE_GUIDANCE, Pf.AGREE, Pf.REFUSE)
class GuidanceAck:
    candidate_id: str = doc("Candidate or case")
    accepted: bool = doc("Whether the guide took the case")


# --- P06 / P07: hand-overs between two roles of the same hub (D2), audited ---------------------
@payload(P.DECLARE_INCIDENT, Pf.INFORM, local=True)
class Declaration:
    """Verifier -> coordinator: the candidate is now a verified case (exclusive ownership, OS1)."""
    case_id: str = doc("Case id (same as the candidate id)")
    priority: str = doc("P1 | P2 | P3")
    confidence: float = doc("Fused probability of a real incident")
    cell: int = doc("Cell of the case")
    rule: str = doc("Which branch of OS4 allowed the declaration")
    sources: list = doc("Pseudonyms of the independent sources", factory=list)


@payload(P.RETRACT_INCIDENT, Pf.INFORM, local=True)
class Retraction:
    case_id: str = doc("Case being retracted")
    reason: str = doc("New contrary evidence")
    confidence: float = doc("Revised confidence")


# --- P08 CallForResponders (FIPA Contract Net) -------------------------------------------------
@payload(P.CALL_FOR_RESPONDERS, Pf.CFP)
class CallForProposals:
    """Announce the tasks of a case to volunteers of the cell and its neighbours."""
    case_id: str = doc("Case (thread)")
    tasks: dict = doc("Task type -> number of responders wanted, e.g. {GO_TO_PATIENT: 2, FETCH_AED: 1}")
    cell: int = doc("Cell of the case; volunteers estimate their ETA to its centre")
    priority: str = doc("P1 | P2 | P3")
    min_qualification: str = doc("Minimum qualification for GO_TO_PATIENT")
    reply_by: float = doc("Deadline for proposals")
    candidate_aeds: list = doc("For FETCH_AED: [{aed_id, pos}] of available AEDs (public registry)",
                               factory=list)


@payload(P.CALL_FOR_RESPONDERS, Pf.PROPOSE)
class Proposal:
    """A volunteer's bid. ETAs are computed on the volunteer's phone; its position never leaves it."""
    case_id: str = doc("Case being bid for")
    offers: list = doc("[{task, eta_s, aed_id?}]: one entry per task the volunteer can do")
    qualification: str = doc("NONE | BLS | BLS_AED | HEALTH_PRO")
    eta_confidence: float = doc("Volunteer's confidence in its ETA", 0.8)


@payload(P.CALL_FOR_RESPONDERS, Pf.REFUSE)
class ProposalRefusal:
    case_id: str = doc("Case")
    reason: str = doc("busy | declined | unqualified | load_cap")


# --- P09 AwardTask ----------------------------------------------------------------------------
@payload(P.AWARD_TASK, Pf.ACCEPT_PROPOSAL)
class Award:
    """The only message that gives a volunteer the patient's precise location (OS5)."""
    case_id: str = doc("Case")
    task: str = doc("GO_TO_PATIENT | FETCH_AED")
    location: list = doc("Precise patient location [x, y]")
    arrive_by: float = doc("ETA + δ; after it the task counts as at risk (OL6)")
    aed_id: int | None = doc("AED to fetch (FETCH_AED)", None)
    reservation_ref: str | None = doc("Reservation to present at the cabinet (FETCH_AED)", None)
    award_token: str | None = doc("Proof of award checked by the AED custodian (FETCH_AED)", None)
    access_notes: str = doc("Building access notes, if disclosed", "")
    guide: str | None = doc("Witness device running guidance on scene, for the takeover (P18)", None)


@payload(P.AWARD_TASK, Pf.REJECT_PROPOSAL)
class AwardRejection:
    case_id: str = doc("Case whose call the bidder did not win")


@payload(P.AWARD_TASK, Pf.INFORM)
class AwardConfirmation:
    case_id: str = doc("Case")
    task: str = doc("Task the volunteer is now committed to (OS2: at most one)")


@payload(P.AWARD_TASK, Pf.FAILURE)
class AwardFailure:
    case_id: str = doc("Case")
    reason: str = doc("busy: committed elsewhere since bidding")


# --- P10 RequestAmbulance (Contract Net with priority) -----------------------------------------
@payload(P.REQUEST_AMBULANCE, Pf.CFP)
class AmbulanceCall:
    case_id: str = doc("Case (thread)")
    priority: str = doc("P1 | P2")
    cell: int = doc("Cell of the case")
    reply_by: float = doc("Deadline for proposals")


@payload(P.REQUEST_AMBULANCE, Pf.PROPOSE)
class AmbulanceProposal:
    case_id: str = doc("Case")
    eta_s: float = doc("Estimated time to the cell centre, including dispatch delay")
    preempts: str | None = doc("P3 case the unit would leave (OS9)", None)


@payload(P.REQUEST_AMBULANCE, Pf.REFUSE)
class AmbulanceRefusal:
    case_id: str = doc("Case")
    reason: str = doc("busy | out_of_service")


@payload(P.REQUEST_AMBULANCE, Pf.ACCEPT_PROPOSAL)
class AmbulanceAward:
    case_id: str = doc("Case")
    priority: str = doc("P1 | P2")
    location: list = doc("Precise patient location [x, y]")


@payload(P.REQUEST_AMBULANCE, Pf.REJECT_PROPOSAL)
class AmbulanceRejection:
    case_id: str = doc("Case")


@payload(P.REQUEST_AMBULANCE, Pf.INFORM)
class AmbulanceConfirmation:
    case_id: str = doc("Case the unit is now committed to")


@payload(P.REQUEST_AMBULANCE, Pf.FAILURE)
class AmbulanceFailure:
    case_id: str = doc("Case")
    reason: str = doc("busy since proposing")


# --- P11 ReserveAED ---------------------------------------------------------------------------
@payload(P.RESERVE_AED, Pf.REQUEST)
class AEDReservationRequest:
    case_id: str = doc("Case (thread)")
    aed_id: int = doc("AED to reserve")
    valid_for_s: float = doc("Requested validity (T_code)")
    priority: str = doc("Case priority")
    award_token: str = doc("Token the runner will present at retrieval")


@payload(P.RESERVE_AED, Pf.AGREE)
class AEDReservation:
    case_id: str = doc("Case")
    aed_id: int = doc("Reserved AED (OS3: one active reservation per AED)")
    reservation_ref: str = doc("Reference to present at retrieval")
    expires_at: float = doc("Reservation expiry")


@payload(P.RESERVE_AED, Pf.REFUSE)
class AEDReservationRefusal:
    case_id: str = doc("Case")
    aed_id: int = doc("AED")
    reason: str = doc("reserved | in_use | unavailable")


@payload(P.RESERVE_AED, Pf.CANCEL)
class AEDReservationCancel:
    case_id: str = doc("Case")
    aed_id: int = doc("AED")
    reservation_ref: str = doc("Reservation to cancel")


# --- P12 RetrieveAED --------------------------------------------------------------------------
@payload(P.RETRIEVE_AED, Pf.REQUEST)
class AEDRetrieval:
    case_id: str = doc("Case (thread)")
    aed_id: int = doc("AED to unlock")
    reservation_ref: str = doc("Reservation reference from the award")
    award_token: str = doc("Proof of award")


@payload(P.RETRIEVE_AED, Pf.INFORM)
class AEDUnlock:
    case_id: str = doc("Case")
    aed_id: int = doc("AED")
    access_code: str = doc("Single-use unlock code")


@payload(P.RETRIEVE_AED, Pf.FAILURE)
class AEDRetrievalFailure:
    case_id: str = doc("Case")
    aed_id: int = doc("AED")
    reason: str = doc("missing_or_faulty | invalid_reservation | expired")


# --- P13 StatusUpdate -------------------------------------------------------------------------
@payload(P.STATUS_UPDATE, Pf.INFORM)
class StatusReport:
    case_id: str = doc("Case (thread)")
    status: str = doc("EN_ROUTE | AT_AED | AED_OK | AED_MISSING | ON_SCENE | CPR_STARTED | AED_DELIVERED | "
                      "SHOCK_DELIVERED | WITNESS_SILENT | EMS_TOOK_OVER | CLINICAL_CONFIRMATION | TRANSPORTING | "
                      "WITHDRAWN | UNSAFE_SCENE")
    t_status: float = doc("When the status changed")
    eta_s: float | None = doc("Remaining ETA, for EN_ROUTE", None)
    detail: dict = doc("Status-specific data, e.g. {real_incident: bool} for CLINICAL_CONFIRMATION",
                       factory=dict)


@payload(P.STATUS_UPDATE, Pf.INFORM)
class OnSceneRoster:
    """Coordinator's answer to an EMS ON_SCENE status: who is there to hand over (P19)."""
    case_id: str = doc("Case")
    responders: list = doc("Pseudonyms of volunteers on scene", factory=list)


# --- P14 ReleaseResponder ---------------------------------------------------------------------
@payload(P.RELEASE_RESPONDER, Pf.CANCEL)
class Release:
    case_id: str = doc("Case")
    reason: str = doc("enough_on_scene | false_alarm | ems_took_over")


@payload(P.RELEASE_RESPONDER, Pf.INFORM)
class ReleaseAck:
    case_id: str = doc("Case; the responder is available again")


# --- P15 HelpEnRouteNotice --------------------------------------------------------------------
@payload(P.HELP_EN_ROUTE_NOTICE, Pf.INFORM)
class HelpEnRoute:
    case_id: str = doc("Case")
    eta_responder_s: float | None = doc("Earliest volunteer ETA", None)
    eta_aed_s: float | None = doc("AED ETA", None)
    eta_ems_s: float | None = doc("Ambulance ETA", None)


# --- P16 / P17: between the guide app and the helper on the same device (local) ----------------
@payload(P.GIVE_INSTRUCTION, Pf.REQUEST, local=True)
class Instruction:
    case_id: str = doc("Case")
    step: str = doc("Step of guidanceProtocol (OS12)")
    text: str = doc("Short instruction")
    cadence_per_min: int | None = doc("Metronome for compressions", None)
    expected_s: float = doc("Expected duration of the step", 0.0)


@payload(P.REPORT_FEEDBACK, Pf.INFORM, local=True)
class Feedback:
    case_id: str = doc("Case")
    result: str = doc("DONE | CANNOT | BREATHING | WOKE_UP | TIRED | AED_ARRIVED")
    t_feedback: float = doc("When the helper reported")


# --- P18 TakeoverFromBystander ----------------------------------------------------------------
@payload(P.TAKEOVER_FROM_BYSTANDER, Pf.REQUEST)
class TakeoverRequest:
    case_id: str = doc("Case")
    arriving_role: str = doc("Role of whoever arrives (never their identity)")


@payload(P.TAKEOVER_FROM_BYSTANDER, Pf.INFORM)
class ActionSummary:
    case_id: str = doc("Case")
    cpr_started_at: float | None = doc("When compressions started", None)
    interruptions: int = doc("Number of pauses", 0)
    aed_attached_at: float | None = doc("When the AED was attached", None)
    shocks: int = doc("Shocks delivered", 0)


# --- P19 HandoverToEMS ------------------------------------------------------------------------
@payload(P.HANDOVER_TO_EMS, Pf.REQUEST)
class HandoverRequest:
    case_id: str = doc("Case")


@payload(P.HANDOVER_TO_EMS, Pf.INFORM)
class HandoverSummary:
    case_id: str = doc("Case")
    collapse_estimate_t: float | None = doc("Estimated time of collapse", None)
    cpr_start_t: float | None = doc("When CPR started", None)
    shocks: int = doc("Shocks delivered", 0)
    first_shock_t: float | None = doc("Time of the first shock", None)
    current_state: str = doc("Short description of the patient's state", "")


# --- P20 CloseCase ----------------------------------------------------------------------------
@payload(P.CLOSE_CASE, Pf.INFORM)
class CaseClosure:
    case_id: str = doc("Case")
    outcome: str = doc("FALSE_ALARM | RESOLVED_ON_SCENE | TRANSPORTED | TIMEOUT")
    t_closed: float = doc("Closing time; personal data must be purged by t_closed + T_ret (OS11)")


@payload(P.CLOSE_CASE, Pf.INFORM)
class AEDRelease:
    """Closure notice to the custodian of an AED reserved for the case."""
    case_id: str = doc("Case")
    aed_id: int = doc("AED")
    reservation_ref: str = doc("Reservation being released")


# --- P21 OutcomeFeedback ----------------------------------------------------------------------
@payload(P.OUTCOME_FEEDBACK, Pf.INFORM)
class OutcomeLabels:
    case_id: str = doc("Case")
    labels: list = doc("[{pseudonym, kind: source|responder, success: bool}]; EMS confirmation is the reference")


# --- P22 QueryTrust ---------------------------------------------------------------------------
@payload(P.QUERY_TRUST, Pf.QUERY_REF)
class TrustQuery:
    pseudonyms: list = doc("Pseudonyms to rate")


@payload(P.QUERY_TRUST, Pf.INFORM)
class TrustReply:
    trust: dict = doc("pseudonym -> {trust in [0, 1], n observations}")


# --- P23 ShareReputation ----------------------------------------------------------------------
@payload(P.SHARE_REPUTATION, Pf.INFORM)
class ReputationSummary:
    entries: list = doc("[{pseudonym, alpha, beta, age_s}]")


# --- P24 RequestDisclosure --------------------------------------------------------------------
@payload(P.REQUEST_DISCLOSURE, Pf.REQUEST)
class DisclosureRequest:
    case_id: str = doc("Case (thread)")
    field_name: str = doc("precise_location | building_access | clinical | identity")
    purpose: str = doc("Why the data is needed, e.g. dispatch")
    priority: str = doc("Case priority (vital interests apply to P1/P2)")
    recipients: list = doc("Who will receive the data (need to know)", factory=list)


@payload(P.REQUEST_DISCLOSURE, Pf.INFORM)
class Disclosure:
    case_id: str = doc("Case")
    field_name: str = doc("Field disclosed")
    value: list | dict | str = doc("Data at the authorised granularity")


@payload(P.REQUEST_DISCLOSURE, Pf.REFUSE)
class DisclosureRefusal:
    case_id: str = doc("Case")
    field_name: str = doc("Field refused")
    reason: str = doc("Justification, e.g. not_need_to_know")


# --- P25 RegisterInCell (FIPA Subscribe) ------------------------------------------------------
@payload(P.REGISTER_IN_CELL, Pf.SUBSCRIBE)
class Registration:
    """Make oneself reachable by a hub, without coordinates (D3)."""
    role: str = doc("volunteer | witness | sensor")
    qualification: str = doc("NONE | BLS | BLS_AED | HEALTH_PRO")
    cell: int = doc("The registrant's current cell")
    ring: int = doc("Hop distance from the registrant's cell to the hub's cell")


@payload(P.REGISTER_IN_CELL, Pf.AGREE)
class RegistrationAck:
    hub_cell: int = doc("Cell of the hub that accepted the registration")


@payload(P.REGISTER_IN_CELL, Pf.CANCEL)
class Deregistration:
    role: str = doc("Role being withdrawn (left the area or went off duty)")


# --- P26 CandidateOpen ------------------------------------------------------------------------
@payload(P.CANDIDATE_OPEN, Pf.INFORM)
class CandidateNotice:
    candidate_id: str = doc("Candidate just opened")
    cell: int = doc("Its cell")
    t_open: float = doc("When it was opened")
    event_type: str = doc("Event type of the first alert")


@payload(P.CANDIDATE_OPEN, Pf.INFORM)
class CandidateMerge:
    """Sent by the hub that drops its duplicate to the hub that keeps the candidate (thread = keeper)."""
    candidate_id: str = doc("Candidate being dropped")
    keeper_id: str = doc("Candidate that keeps ownership (first opened, then lower hub id)")
    alerts: list = doc("The dropped candidate's alerts: [{origin, report}] with report an AlertReport dict",
                       factory=list)


# --- P27 ReplicateCase ------------------------------------------------------------------------
@payload(P.REPLICATE_CASE, Pf.INFORM)
class CaseSnapshot:
    """Compact case state for the successor hub; excludes location and clinical data (D7)."""
    case_id: str = doc("Case")
    state: str = doc("Case state")
    priority: str = doc("P1 | P2 | P3")
    cell: int = doc("Cell")
    t_open: float = doc("When the candidate was opened")
    subject: str | None = doc("Guardian to ask again for the location (P24)", None)
    ems: str | None = doc("Ambulance assigned, if any", None)
    awards: dict = doc("volunteer -> {task, eta_s, aed_id, status}", factory=dict)
    guides: list = doc("Witness devices running guidance", factory=list)
    sources: list = doc("Pseudonyms of the case's sources (for outcome labels)", factory=list)
    reservation: dict | None = doc("{aed_id, ref, token} if any", None)
    closed: bool = doc("True once the case is closed (the successor drops it)", False)


@payload(P.REPLICATE_CASE, Pf.INFORM)
class Heartbeat:
    open_cases: list = doc("Case ids still owned by the sender")
    lease_until: float = doc("Lease expiry claimed by the owner")


@payload(P.REPLICATE_CASE, Pf.INFORM)
class HeartbeatAck:
    lease_until: float = doc("Lease expiry acknowledged by the successor")


# --- P28 TakeOverCase -------------------------------------------------------------------------
@payload(P.TAKE_OVER_CASE, Pf.INFORM)
class Takeover:
    case_id: str = doc("Case")
    new_coordinator: str = doc("Pseudonym of the hub now owning the case")

"""Ontology "cemr-v1": protocol identifiers, FIPA performatives and the enumerations used in messages.

Enum values are the English identifiers that travel in messages. Where the Gaia analysis used
Portuguese names, PT_NAMES records the correspondence.
"""

from enum import Enum

ONTOLOGY = "cemr-v1"
LANGUAGE = "json"


class StrEnum(str, Enum):
    """Members compare and hash like their string values, so they work as keys of decoded JSON dicts."""
    __hash__ = str.__hash__

    def __str__(self) -> str:
        return self.value


class Protocol(StrEnum):
    RAISE_CANDIDATE_ALERT = "P01-RaiseCandidateAlert"
    CANCEL_ALERT = "P02-CancelAlert"
    CORROBORATION_REQUEST = "P03-CorroborationRequest"
    TRIAGE_QUESTIONNAIRE = "P04-TriageQuestionnaire"
    ACTIVATE_GUIDANCE = "P05-ActivateGuidance"
    DECLARE_INCIDENT = "P06-DeclareIncident"
    RETRACT_INCIDENT = "P07-RetractIncident"
    CALL_FOR_RESPONDERS = "P08-CallForResponders"
    AWARD_TASK = "P09-AwardTask"
    REQUEST_AMBULANCE = "P10-RequestAmbulance"
    RESERVE_AED = "P11-ReserveAED"
    RETRIEVE_AED = "P12-RetrieveAED"
    STATUS_UPDATE = "P13-StatusUpdate"
    RELEASE_RESPONDER = "P14-ReleaseResponder"
    HELP_EN_ROUTE_NOTICE = "P15-HelpEnRouteNotice"
    GIVE_INSTRUCTION = "P16-GiveInstruction"
    REPORT_FEEDBACK = "P17-ReportFeedback"
    TAKEOVER_FROM_BYSTANDER = "P18-TakeoverFromBystander"
    HANDOVER_TO_EMS = "P19-HandoverToEMS"
    CLOSE_CASE = "P20-CloseCase"
    OUTCOME_FEEDBACK = "P21-OutcomeFeedback"
    QUERY_TRUST = "P22-QueryTrust"
    SHARE_REPUTATION = "P23-ShareReputation"
    REQUEST_DISCLOSURE = "P24-RequestDisclosure"
    REGISTER_IN_CELL = "P25-RegisterInCell"
    CANDIDATE_OPEN = "P26-CandidateOpen"
    REPLICATE_CASE = "P27-ReplicateCase"
    TAKE_OVER_CASE = "P28-TakeOverCase"

    @property
    def code(self) -> str:
        return self.value.split("-", 1)[0]


class Performative(StrEnum):
    INFORM = "inform"
    CANCEL = "cancel"
    QUERY_REF = "query-ref"
    QUERY_IF = "query-if"
    REQUEST = "request"
    AGREE = "agree"
    REFUSE = "refuse"
    FAILURE = "failure"
    CFP = "cfp"
    PROPOSE = "propose"
    ACCEPT_PROPOSAL = "accept-proposal"
    REJECT_PROPOSAL = "reject-proposal"
    SUBSCRIBE = "subscribe"


class Priority(StrEnum):
    """Operational triage (analysis §2.2), not a clinical diagnosis."""
    P1 = "P1"   # suspected cardiac arrest: CPR, AED and ambulance now
    P2 = "P2"   # unconscious but breathing, serious fall, suspected stroke
    P3 = "P3"   # minor fall, conscious person

    @property
    def rank(self) -> int:
        return int(self.value[1])


class SourceKind(StrEnum):
    SENSOR = "sensor"
    WITNESS = "witness"


class EventType(StrEnum):
    COLLAPSE_CARDIAC = "collapse_cardiac"   # fall + immobility + absent/anomalous cardiac signal
    FALL_IMMOBILE = "fall_immobile"         # fall + immobility, cardiac signal present
    FALL = "fall"                           # fall, then movement
    WITNESS_COLLAPSE = "witness_collapse"   # a citizen saw someone collapse

    @property
    def provisional_priority(self) -> "Priority":
        """Worst plausible priority until triage says otherwise (a witness report is treated as P1)."""
        return {"collapse_cardiac": Priority.P1, "fall_immobile": Priority.P2, "fall": Priority.P3,
                "witness_collapse": Priority.P1}[self.value]


class SensorPolicy(StrEnum):
    ADAPTIVE = "adaptive"
    ALERT_FIRST = "alert_first"
    CONFIRM_FIRST = "confirm_first"
    HUMAN = "human"


class PromptStatus(StrEnum):
    PENDING = "pending"
    NO_RESPONSE = "no_response"
    NOT_APPLICABLE = "not_applicable"


class Verdict(StrEnum):
    CONFIRM = "confirm"
    DENY = "deny"
    NO_DATA = "no_data"


class TriageQuestionId(StrEnum):
    """Asked in the order of the basic life support algorithm (analysis P04)."""
    SCENE_SAFE = "scene_safe"
    RESPONSIVE = "responsive"
    BREATHING_NORMALLY = "breathing_normally"
    CALLED_112 = "called_112"


class Answer(StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class RegistrationRole(StrEnum):
    VOLUNTEER = "volunteer"
    WITNESS = "witness"
    SENSOR = "sensor"


class Qualification(StrEnum):
    NONE = "NONE"
    BLS = "BLS"                 # SBV
    BLS_AED = "BLS_AED"         # SBV-DAE
    HEALTH_PRO = "HEALTH_PRO"   # health professional

    @property
    def rank(self) -> int:
        return ["NONE", "BLS", "BLS_AED", "HEALTH_PRO"].index(self.value)


class TaskType(StrEnum):
    GO_TO_PATIENT = "GO_TO_PATIENT"   # IR_AO_DOENTE
    FETCH_AED = "FETCH_AED"           # BUSCAR_DAE


class ResponderStatus(StrEnum):
    EN_ROUTE = "EN_ROUTE"
    AT_AED = "AT_AED"
    AED_OK = "AED_OK"
    AED_MISSING = "AED_MISSING"
    ON_SCENE = "ON_SCENE"
    CPR_STARTED = "CPR_STARTED"
    AED_DELIVERED = "AED_DELIVERED"
    SHOCK_DELIVERED = "SHOCK_DELIVERED"
    WITNESS_SILENT = "WITNESS_SILENT"
    EMS_TOOK_OVER = "EMS_TOOK_OVER"
    CLINICAL_CONFIRMATION = "CLINICAL_CONFIRMATION"
    TRANSPORTING = "TRANSPORTING"
    WITHDRAWN = "WITHDRAWN"
    UNSAFE_SCENE = "UNSAFE_SCENE"


ON_SCENE_STATUSES = {ResponderStatus.ON_SCENE, ResponderStatus.CPR_STARTED,
                     ResponderStatus.AED_DELIVERED, ResponderStatus.SHOCK_DELIVERED}


class AEDState(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    IN_USE = "IN_USE"
    UNAVAILABLE = "UNAVAILABLE"


class EMSState(StrEnum):
    AVAILABLE = "AVAILABLE"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    TRANSPORT = "TRANSPORT"


class CaseState(StrEnum):
    VERIFYING = "VERIFYING"
    DECLARED = "DECLARED"
    DISPATCHING = "DISPATCHING"
    TRACKING = "TRACKING"
    CLOSED = "CLOSED"
    DISCARDED = "DISCARDED"


class Outcome(StrEnum):
    FALSE_ALARM = "FALSE_ALARM"
    RESOLVED_ON_SCENE = "RESOLVED_ON_SCENE"
    TRANSPORTED = "TRANSPORTED"
    TIMEOUT = "TIMEOUT"


class DisclosureField(StrEnum):
    PRECISE_LOCATION = "precise_location"
    BUILDING_ACCESS = "building_access"
    CLINICAL = "clinical"
    IDENTITY = "identity"


class CancelReason(StrEnum):
    WEARER_OK = "wearer_ok"
    WITNESS_RETRACTS = "witness_retracts"


# Correspondence with the Portuguese identifiers of the Gaia analysis.
PT_NAMES = {
    "IR_AO_DOENTE": TaskType.GO_TO_PATIENT,
    "BUSCAR_DAE": TaskType.FETCH_AED,
    "A_CAMINHO": ResponderStatus.EN_ROUTE,
    "NO_DAE": ResponderStatus.AT_AED,
    "DAE_OK": ResponderStatus.AED_OK,
    "DAE_EM_FALTA": ResponderStatus.AED_MISSING,
    "NO_LOCAL": ResponderStatus.ON_SCENE,
    "RCP_INICIADA": ResponderStatus.CPR_STARTED,
    "CHOQUE": ResponderStatus.SHOCK_DELIVERED,
    "TESTEMUNHA_SILENCIOSA": ResponderStatus.WITNESS_SILENT,
    "EMS_ASSUMIU": ResponderStatus.EMS_TOOK_OVER,
    "DESISTÊNCIA": ResponderStatus.WITHDRAWN,
    "CONFIRMAÇÃO_CLÍNICA": ResponderStatus.CLINICAL_CONFIRMATION,
    "DISPONÍVEL": AEDState.AVAILABLE,
    "RESERVADO": AEDState.RESERVED,
    "EM_USO": AEDState.IN_USE,
    "INDISPONÍVEL": AEDState.UNAVAILABLE,
    "EM_MARCHA": EMSState.EN_ROUTE,
    "TRANSPORTE": EMSState.TRANSPORT,
    "FALSO_ALARME": Outcome.FALSE_ALARM,
    "RESOLVIDO_NO_LOCAL": Outcome.RESOLVED_ON_SCENE,
    "TRANSPORTADO": Outcome.TRANSPORTED,
}

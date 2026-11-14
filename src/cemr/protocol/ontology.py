"""Ontologia "cemr-v1": identificadores dos protocolos, performativas FIPA e valores enumerados.

Os valores dos enumerados são os identificadores em inglês que viajam nas mensagens. A
correspondência com os nomes em português da análise Gaia está na tabela final de
docs/04-protocols-and-messages.md.
"""

from enum import Enum

ONTOLOGY = "cemr-v1"
LANGUAGE = "json"


class StrEnum(str, Enum):
    """Enumerado cujos membros se comportam como a string do seu valor.

    Assim podem ser chaves de dicionários vindos de JSON e comparados diretamente com texto.
    """

    __hash__ = str.__hash__

    def __str__(self) -> str:
        return self.value


class Protocol(StrEnum):
    """Protocolos do modelo de interação (P01-P28).

    O P22 QueryTrust da análise não tem mensagens: o coordenador e o gestor de reputação são o
    mesmo agente (o hub, decisão D2), por isso a consulta é uma leitura da tabela de confiança.
    """

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
    SHARE_REPUTATION = "P23-ShareReputation"
    REQUEST_DISCLOSURE = "P24-RequestDisclosure"
    REGISTER_IN_CELL = "P25-RegisterInCell"
    CANDIDATE_OPEN = "P26-CandidateOpen"
    REPLICATE_CASE = "P27-ReplicateCase"
    TAKE_OVER_CASE = "P28-TakeOverCase"

    @property
    def code(self) -> str:
        """O código curto do protocolo, por exemplo "P08"."""
        return self.value.split("-")[0]


class Performative(StrEnum):
    """Performativas FIPA-ACL usadas, com o significado da especificação."""

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
    """Triagem operacional (análise §2.2), não um diagnóstico clínico."""

    P1 = "P1"   # suspeita de paragem cardíaca: RCP, DAE e ambulância já
    P2 = "P2"   # inconsciente mas a respirar, queda grave, suspeita de AVC
    P3 = "P3"   # queda ligeira, pessoa consciente

    @property
    def rank(self) -> int:
        """1 para P1 (a mais grave), 2 para P2, 3 para P3."""
        return int(self.value[1])


class SourceKind(StrEnum):
    """Tipo de fonte de um alerta."""

    SENSOR = "sensor"
    WITNESS = "witness"


class EventType(StrEnum):
    """Tipo de evento reportado num alerta P01."""

    COLLAPSE_CARDIAC = "collapse_cardiac"   # queda + imobilidade + sinal cardíaco ausente ou anómalo
    FALL_IMMOBILE = "fall_immobile"         # queda + imobilidade, com sinal cardíaco
    FALL = "fall"                           # queda e depois movimento
    WITNESS_COLLAPSE = "witness_collapse"   # um cidadão viu alguém cair

    @property
    def provisional_priority(self) -> "Priority":
        """A pior prioridade plausível até a triagem dizer o contrário (um relato de testemunha vale P1)."""
        if self in (EventType.COLLAPSE_CARDIAC, EventType.WITNESS_COLLAPSE):
            return Priority.P1
        if self == EventType.FALL_IMMOBILE:
            return Priority.P2
        return Priority.P3


class SensorPolicy(StrEnum):
    """Política do dispositivo: alertar primeiro ou confirmar com o portador primeiro."""

    ADAPTIVE = "adaptive"
    ALERT_FIRST = "alert_first"
    CONFIRM_FIRST = "confirm_first"
    HUMAN = "human"


class PromptStatus(StrEnum):
    """Estado do aviso "Está bem?" mostrado ao portador do dispositivo."""

    PENDING = "pending"
    NO_RESPONSE = "no_response"
    NOT_APPLICABLE = "not_applicable"


class Verdict(StrEnum):
    """Resposta a um pedido de corroboração P03."""

    CONFIRM = "confirm"
    DENY = "deny"
    NO_DATA = "no_data"


class TriageQuestionId(StrEnum):
    """Perguntas da triagem P04, pela ordem do algoritmo de suporte básico de vida."""

    SCENE_SAFE = "scene_safe"
    RESPONSIVE = "responsive"
    BREATHING_NORMALLY = "breathing_normally"
    CALLED_112 = "called_112"


class Answer(StrEnum):
    """Resposta a uma pergunta da triagem."""

    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class RegistrationRole(StrEnum):
    """Papel com que um agente se regista no hub (P25)."""

    VOLUNTEER = "volunteer"
    WITNESS = "witness"
    SENSOR = "sensor"


class Qualification(StrEnum):
    """Qualificação de um voluntário."""

    NONE = "NONE"
    BLS = "BLS"                 # SBV
    BLS_AED = "BLS_AED"         # SBV-DAE
    HEALTH_PRO = "HEALTH_PRO"   # profissional de saúde

    @property
    def rank(self) -> int:
        """Posição na escala de qualificação (0 = nenhuma)."""
        return list(Qualification).index(self)


class TaskType(StrEnum):
    """Tarefas que um caso pede aos voluntários."""

    GO_TO_PATIENT = "GO_TO_PATIENT"   # IR_AO_DOENTE
    FETCH_AED = "FETCH_AED"           # BUSCAR_DAE


class ResponderStatus(StrEnum):
    """Estados reportados por voluntários, testemunhas e ambulâncias (P13)."""

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
    """Estado de um DAE no registo público (aedRegistry)."""

    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    IN_USE = "IN_USE"
    UNAVAILABLE = "UNAVAILABLE"


class EMSState(StrEnum):
    """Estado de uma ambulância."""

    AVAILABLE = "AVAILABLE"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    TRANSPORT = "TRANSPORT"


class CaseState(StrEnum):
    """Estado de um candidato ou caso no hub."""

    VERIFYING = "VERIFYING"
    DECLARED = "DECLARED"
    DISPATCHING = "DISPATCHING"
    TRACKING = "TRACKING"
    CLOSED = "CLOSED"
    DISCARDED = "DISCARDED"


class Outcome(StrEnum):
    """Resultado com que um caso é fechado."""

    FALSE_ALARM = "FALSE_ALARM"
    RESOLVED_ON_SCENE = "RESOLVED_ON_SCENE"
    TRANSPORTED = "TRANSPORTED"
    TIMEOUT = "TIMEOUT"


class DisclosureField(StrEnum):
    """Dados pessoais que podem ser pedidos por P24."""

    PRECISE_LOCATION = "precise_location"
    BUILDING_ACCESS = "building_access"
    CLINICAL = "clinical"
    IDENTITY = "identity"


class CancelReason(StrEnum):
    """Motivo de um cancelamento P02."""

    WEARER_OK = "wearer_ok"
    WITNESS_RETRACTS = "witness_retracts"

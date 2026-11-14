"""Mensagens da deteção e verificação (sub-organização SO-DV): protocolos P01 a P07.

Cada mensagem é uma dataclass com dois atributos de classe: PROTOCOL, o protocolo a que pertence,
e PERFORMATIVES, as performativas FIPA com que pode viajar (a primeira é a habitual). Convenções:
o JID do remetente é o seu pseudónimo estável (D7), por isso as mensagens não o repetem; as
posições são [x, y] em metros e só aparecem nas mensagens autorizadas a levá-las (OS5); os tempos
são segundos simulados desde o início do run. Esquemas em docs/04-protocols-and-messages.md §5.
"""

from dataclasses import dataclass, field

from .ontology import Performative as Pf
from .ontology import Protocol


@dataclass
class AlertReport:
    """P01: suspeita de colapso, de um dispositivo (SensorMonitor) ou de um cidadão (WitnessReporter).

    É reenviado na mesma thread para atualizar o estado do aviso ao portador.

    Attributes:
        alert_id (str): Único por fonte; é também a thread da conversa.
        source_kind (str): "sensor" ou "witness".
        event_type (str): collapse_cardiac, fall_immobile, fall ou witness_collapse.
        confidence (float): Confiança local da fonte, entre 0 e 1.
        cell (int): Localização grosseira: só o id da célula (D7).
        t_event (float): Quando o evento foi detetado ou visto.
        policy (str): alert_first, confirm_first ou human.
        prompt_status (str): Aviso ao portador: pending, no_response ou not_applicable.
        origin (str | None): Fonte original, quando um hub reencaminha o alerta depois de uma fusão (P26).
    """

    PROTOCOL = Protocol.RAISE_CANDIDATE_ALERT
    PERFORMATIVES = (Pf.INFORM,)

    alert_id: str
    source_kind: str
    event_type: str
    confidence: float
    cell: int
    t_event: float
    policy: str
    prompt_status: str
    origin: str | None = None


@dataclass
class AlertAck:
    """P01: recibo do hub; o alerta juntou-se ao candidato `candidate_id`.

    Attributes:
        alert_id (str): Alerta confirmado.
        candidate_id (str): Candidato (mais tarde caso) a que o alerta foi juntado.
    """

    PROTOCOL = Protocol.RAISE_CANDIDATE_ALERT
    PERFORMATIVES = (Pf.INFORM,)

    alert_id: str
    candidate_id: str


@dataclass
class AlertCancel:
    """P02: o portador respondeu "estou bem" ou a testemunha retirou o relato.

    Attributes:
        alert_id (str): Alerta a cancelar.
        reason (str): wearer_ok ou witness_retracts.
        t_event (float): Quando o cancelamento aconteceu.
        origin (str | None): Fonte original, quando reencaminhado por um hub.
    """

    PROTOCOL = Protocol.CANCEL_ALERT
    PERFORMATIVES = (Pf.CANCEL,)

    alert_id: str
    reason: str
    t_event: float
    origin: str | None = None


@dataclass
class CancelAck:
    """P02: recibo do cancelamento.

    Attributes:
        alert_id (str): Alerta cancelado.
        candidate_state (str): Estado do candidato depois do cancelamento.
    """

    PROTOCOL = Protocol.CANCEL_ALERT
    PERFORMATIVES = (Pf.INFORM,)

    alert_id: str
    candidate_state: str


@dataclass
class CorroborationQuery:
    """P03: pede evidência independente às fontes próximas.

    Nunca inclui a localização exata nem a identidade do doente.

    Attributes:
        candidate_id (str): Candidato em verificação (thread).
        cell (int): Célula do candidato.
        window_from (float): Início da janela temporal de interesse.
        window_to (float): Fim da janela temporal de interesse.
        reply_by (float): Prazo; sem resposta conta como no_data.
    """

    PROTOCOL = Protocol.CORROBORATION_REQUEST
    PERFORMATIVES = (Pf.QUERY_REF,)

    candidate_id: str
    cell: int
    window_from: float
    window_to: float
    reply_by: float


@dataclass
class CorroborationReply:
    """P03: resumo da evidência de uma fonte próxima (só um veredicto e uma confiança).

    Attributes:
        candidate_id (str): Candidato a corroborar.
        verdict (str): confirm, deny ou no_data.
        confidence (float): Confiança da evidência resumida, entre 0 e 1.
    """

    PROTOCOL = Protocol.CORROBORATION_REQUEST
    PERFORMATIVES = (Pf.INFORM,)

    candidate_id: str
    verdict: str
    confidence: float


@dataclass
class CorroborationRefusal:
    """P03: a fonte recusa partilhar evidência.

    Attributes:
        candidate_id (str): Candidato a corroborar.
        reason (str): Por exemplo consent, quando a política do dono não permite partilhar.
    """

    PROTOCOL = Protocol.CORROBORATION_REQUEST
    PERFORMATIVES = (Pf.REFUSE,)

    candidate_id: str
    reason: str


@dataclass
class TriageQuestion:
    """P04: uma pergunta a uma testemunha no local, pela ordem do suporte básico de vida.

    Attributes:
        candidate_id (str): Candidato em verificação (thread).
        question (str): scene_safe, responsive, breathing_normally ou called_112.
        reply_by (float): Prazo da resposta.
    """

    PROTOCOL = Protocol.TRIAGE_QUESTIONNAIRE
    PERFORMATIVES = (Pf.QUERY_IF,)

    candidate_id: str
    question: str
    reply_by: float


@dataclass
class TriageAnswer:
    """P04: resposta da testemunha.

    Attributes:
        candidate_id (str): Candidato em verificação.
        question (str): Pergunta respondida.
        answer (str): yes, no ou unknown (o silêncio conta como unknown).
        t_answer (float): Quando a testemunha respondeu.
    """

    PROTOCOL = Protocol.TRIAGE_QUESTIONNAIRE
    PERFORMATIVES = (Pf.INFORM,)

    candidate_id: str
    question: str
    answer: str
    t_answer: float


@dataclass
class GuidanceActivation:
    """P05: liga a orientação passo a passo no telemóvel da testemunha, antes do fim da verificação.

    Attributes:
        candidate_id (str): Candidato ou caso (thread).
        priority (str): Prioridade provisória.
        triage (dict): Respostas já obtidas na triagem, para a app não as repetir.
    """

    PROTOCOL = Protocol.ACTIVATE_GUIDANCE
    PERFORMATIVES = (Pf.REQUEST,)

    candidate_id: str
    priority: str
    triage: dict = field(default_factory=dict)


@dataclass
class GuidanceAck:
    """P05: a app aceita (agree) ou recusa (refuse) orientar o caso.

    Attributes:
        candidate_id (str): Candidato ou caso.
        accepted (bool): Se a app ficou com o caso.
    """

    PROTOCOL = Protocol.ACTIVATE_GUIDANCE
    PERFORMATIVES = (Pf.AGREE, Pf.REFUSE)

    candidate_id: str
    accepted: bool


@dataclass
class Declaration:
    """P06: passagem do verificador para o coordenador, dentro do mesmo hub (D2); fica auditada.

    A partir daqui o caso tem um único dono (OS1).

    Attributes:
        case_id (str): Id do caso (igual ao do candidato).
        priority (str): P1, P2 ou P3.
        confidence (float): Probabilidade fundida de ser um incidente real.
        cell (int): Célula do caso.
        rule (str): Ramo da regra OS4 que permitiu declarar.
        sources (list): Pseudónimos das fontes independentes.
    """

    PROTOCOL = Protocol.DECLARE_INCIDENT
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    priority: str
    confidence: float
    cell: int
    rule: str
    sources: list = field(default_factory=list)


@dataclass
class Retraction:
    """P07: o coordenador desfaz uma declaração (local ao hub, auditado).

    Attributes:
        case_id (str): Caso retirado.
        reason (str): Nova evidência contrária.
        confidence (float): Confiança revista.
    """

    PROTOCOL = Protocol.RETRACT_INCIDENT
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    reason: str
    confidence: float

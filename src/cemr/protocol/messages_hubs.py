"""Mensagens de reputação, privacidade e coordenação entre hubs: P21 e P23 a P28.

P21 e P23 são do gestor de reputação (D6), P24 do guardião de privacidade (D7), P25 do registo
nas células (D3), P26 da deteção de duplicados na fronteira e P27/P28 do failover (D8).
As convenções são as de `messages_detection`.
"""

from dataclasses import dataclass, field

from .ontology import Performative as Pf
from .ontology import Protocol


@dataclass
class OutcomeLabels:
    """P21 (local ao hub): rótulos de resultado para a reputação, escritos no fecho do caso.

    Attributes:
        case_id (str): Caso.
        labels (list): [{pseudonym, kind: source|responder, success: bool}]; a confirmação da EMS é a referência.
    """

    PROTOCOL = Protocol.OUTCOME_FEEDBACK
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    labels: list


@dataclass
class ReputationSummary:
    """P23: resumo das contagens próprias de um hub, enviado aos vizinhos.

    Attributes:
        entries (list): [{pseudonym, alpha, beta}].
    """

    PROTOCOL = Protocol.SHARE_REPUTATION
    PERFORMATIVES = (Pf.INFORM,)

    entries: list


@dataclass
class DisclosureRequest:
    """P24 (request): pedido de um dado pessoal ao guardião do titular.

    Attributes:
        case_id (str): Caso (thread).
        field_name (str): precise_location, building_access, clinical ou identity.
        purpose (str): Para que é preciso o dado, por exemplo dispatch.
        priority (str): Prioridade do caso (os interesses vitais aplicam-se a P1/P2).
        recipients (list): Quem vai receber o dado (necessidade de saber).
    """

    PROTOCOL = Protocol.REQUEST_DISCLOSURE
    PERFORMATIVES = (Pf.REQUEST,)

    case_id: str
    field_name: str
    purpose: str
    priority: str
    recipients: list = field(default_factory=list)


@dataclass
class Disclosure:
    """P24 (inform): o dado, na granularidade autorizada.

    Attributes:
        case_id (str): Caso.
        field_name (str): Campo divulgado.
        value (list | dict | str): O dado.
    """

    PROTOCOL = Protocol.REQUEST_DISCLOSURE
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    field_name: str
    value: list | dict | str


@dataclass
class DisclosureRefusal:
    """P24 (refuse): o guardião recusa.

    Attributes:
        case_id (str): Caso.
        field_name (str): Campo recusado.
        reason (str): Justificação, por exemplo not_need_to_know.
    """

    PROTOCOL = Protocol.REQUEST_DISCLOSURE
    PERFORMATIVES = (Pf.REFUSE,)

    case_id: str
    field_name: str
    reason: str


@dataclass
class Registration:
    """P25 (subscribe): torna o remetente contactável por um hub, sem coordenadas (D3).

    Attributes:
        role (str): volunteer, witness ou sensor.
        qualification (str): NONE, BLS, BLS_AED ou HEALTH_PRO.
        cell (int): Célula atual de quem se regista.
        ring (int): Distância em saltos da célula de quem se regista à célula do hub.
    """

    PROTOCOL = Protocol.REGISTER_IN_CELL
    PERFORMATIVES = (Pf.SUBSCRIBE,)

    role: str
    qualification: str
    cell: int
    ring: int


@dataclass
class RegistrationAck:
    """P25 (agree): o hub aceitou o registo.

    Attributes:
        hub_cell (int): Célula do hub.
    """

    PROTOCOL = Protocol.REGISTER_IN_CELL
    PERFORMATIVES = (Pf.AGREE,)

    hub_cell: int


@dataclass
class Deregistration:
    """P25 (cancel): o agente deixou a zona ou saiu de serviço.

    Attributes:
        role (str): Papel retirado.
    """

    PROTOCOL = Protocol.REGISTER_IN_CELL
    PERFORMATIVES = (Pf.CANCEL,)

    role: str


@dataclass
class CandidateNotice:
    """P26: um hub abriu um candidato; os vizinhos verificam se é o mesmo incidente.

    Também é a resposta de um hub com o mesmo incidente aberto antes, para o outro largar o seu.

    Attributes:
        candidate_id (str): Candidato acabado de abrir.
        cell (int): A sua célula.
        area (list | None): Área do primeiro alerta (~100 m).
        t_open (float): Quando foi aberto.
        event_type (str): Tipo de evento do primeiro alerta.
    """

    PROTOCOL = Protocol.CANDIDATE_OPEN
    PERFORMATIVES = (Pf.INFORM,)

    candidate_id: str
    cell: int
    area: list | None
    t_open: float
    event_type: str


@dataclass
class CandidateMerge:
    """P26: enviado pelo hub que larga o seu duplicado ao hub que fica com o candidato.

    Attributes:
        candidate_id (str): Candidato largado.
        keeper_id (str): Candidato que fica (o aberto primeiro; em empate, o do hub de menor id).
        alerts (list): Alertas do candidato largado, [{origin, report}], com report um AlertReport em dict.
    """

    PROTOCOL = Protocol.CANDIDATE_OPEN
    PERFORMATIVES = (Pf.INFORM,)

    candidate_id: str
    keeper_id: str
    alerts: list = field(default_factory=list)


@dataclass
class CaseSnapshot:
    """P27: estado compacto de um caso para o hub sucessor; sem localização nem dados clínicos (D7).

    Attributes:
        case_id (str): Caso.
        state (str): Estado do caso.
        priority (str): P1, P2 ou P3.
        cell (int): Célula.
        t_open (float): Quando o candidato foi aberto.
        subject (str | None): Guardião a quem voltar a pedir a localização (P24).
        ems (str | None): Ambulância adjudicada, se houver.
        awards (dict): Voluntário -> {task, eta_s, aed_id, status, ...}.
        guides (list): Telemóveis de testemunhas com orientação ativa.
        sources (list): Pseudónimos das fontes do caso (para os rótulos de resultado).
        reservation (dict | None): {aed_id, ref, token}, se houver reserva.
        closed (bool): True quando o caso fechou (o sucessor esquece-o).
    """

    PROTOCOL = Protocol.REPLICATE_CASE
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    state: str
    priority: str
    cell: int
    t_open: float
    subject: str | None = None
    ems: str | None = None
    awards: dict = field(default_factory=dict)
    guides: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    reservation: dict | None = None
    closed: bool = False


@dataclass
class Heartbeat:
    """P27: sinal de vida do hub dono para o seu sucessor.

    Attributes:
        open_cases (list): Ids dos casos que o remetente ainda tem.
        lease_until (float): Fim da lease pedida pelo dono.
    """

    PROTOCOL = Protocol.REPLICATE_CASE
    PERFORMATIVES = (Pf.INFORM,)

    open_cases: list
    lease_until: float


@dataclass
class HeartbeatAck:
    """P27: o sucessor confirma a lease.

    Attributes:
        lease_until (float): Fim da lease confirmada.
    """

    PROTOCOL = Protocol.REPLICATE_CASE
    PERFORMATIVES = (Pf.INFORM,)

    lease_until: float


@dataclass
class Takeover:
    """P28: o sucessor avisa os participantes de que passou a coordenar o caso.

    Attributes:
        case_id (str): Caso.
        new_coordinator (str): Pseudónimo do hub que agora é dono do caso.
    """

    PROTOCOL = Protocol.TAKE_OVER_CASE
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    new_coordinator: str

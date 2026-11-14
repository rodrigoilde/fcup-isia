"""Mensagens do despacho por Contract Net (sub-organização SO-DR): protocolos P08 a P10.

As convenções são as de `messages_detection`. Os três protocolos seguem o Contract Net da FIPA:
cfp, depois propose ou refuse, depois accept-proposal ou reject-proposal, e por fim inform ou failure.
"""

from dataclasses import dataclass, field

from .ontology import Performative as Pf
from .ontology import Protocol


@dataclass
class CallForProposals:
    """P08 (cfp): anuncia as tarefas de um caso aos voluntários da célula e das vizinhas.

    Attributes:
        case_id (str): Caso (thread).
        tasks (dict): Tarefa -> número de voluntários pedidos, por exemplo {GO_TO_PATIENT: 2, FETCH_AED: 1}.
        cell (int): Célula do caso; os voluntários estimam o ETA até ao seu centro.
        priority (str): P1, P2 ou P3.
        min_qualification (str): Qualificação mínima para GO_TO_PATIENT.
        reply_by (float): Prazo das propostas.
        candidate_aeds (list): Para FETCH_AED, [{aed_id, pos}] dos DAE disponíveis (registo público).
    """

    PROTOCOL = Protocol.CALL_FOR_RESPONDERS
    PERFORMATIVES = (Pf.CFP,)

    case_id: str
    tasks: dict
    cell: int
    priority: str
    min_qualification: str
    reply_by: float
    candidate_aeds: list = field(default_factory=list)


@dataclass
class Proposal:
    """P08 (propose): a proposta de um voluntário.

    Os ETA são calculados no telemóvel do voluntário; a sua posição nunca sai de lá.

    Attributes:
        case_id (str): Caso a que se propõe.
        offers (list): [{task, eta_s, aed_id?}], uma entrada por tarefa que o voluntário pode fazer.
        qualification (str): NONE, BLS, BLS_AED ou HEALTH_PRO.
    """

    PROTOCOL = Protocol.CALL_FOR_RESPONDERS
    PERFORMATIVES = (Pf.PROPOSE,)

    case_id: str
    offers: list
    qualification: str


@dataclass
class ProposalRefusal:
    """P08 (refuse): o voluntário não se propõe.

    Attributes:
        case_id (str): Caso.
        reason (str): busy, declined, unqualified ou load_cap.
    """

    PROTOCOL = Protocol.CALL_FOR_RESPONDERS
    PERFORMATIVES = (Pf.REFUSE,)

    case_id: str
    reason: str


@dataclass
class Award:
    """P09 (accept-proposal): a única mensagem que dá a um voluntário a localização exata (OS5).

    Attributes:
        case_id (str): Caso.
        task (str): GO_TO_PATIENT ou FETCH_AED.
        location (list): Localização exata do doente, [x, y].
        arrive_by (float): ETA + δ; depois disto a tarefa conta como em risco (OL6).
        aed_id (int | None): DAE a ir buscar (FETCH_AED).
        reservation_ref (str | None): Reserva a apresentar no armário (FETCH_AED).
        award_token (str | None): Prova da adjudicação, conferida pelo guardião do DAE (FETCH_AED).
        guide (str | None): Telemóvel da testemunha com orientação ativa no local, para o P18.
    """

    PROTOCOL = Protocol.AWARD_TASK
    PERFORMATIVES = (Pf.ACCEPT_PROPOSAL,)

    case_id: str
    task: str
    location: list
    arrive_by: float
    aed_id: int | None = None
    reservation_ref: str | None = None
    award_token: str | None = None
    guide: str | None = None


@dataclass
class AwardRejection:
    """P09 (reject-proposal): a proposta não ganhou.

    Attributes:
        case_id (str): Caso.
    """

    PROTOCOL = Protocol.AWARD_TASK
    PERFORMATIVES = (Pf.REJECT_PROPOSAL,)

    case_id: str


@dataclass
class AwardConfirmation:
    """P09 (inform): o voluntário compromete-se com a tarefa.

    Attributes:
        case_id (str): Caso.
        task (str): Tarefa com que fica comprometido (OS2: no máximo uma).
    """

    PROTOCOL = Protocol.AWARD_TASK
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    task: str


@dataclass
class AwardFailure:
    """P09 (failure): o voluntário já não pode cumprir.

    Attributes:
        case_id (str): Caso.
        reason (str): busy, quando se comprometeu com outro caso depois de propor.
    """

    PROTOCOL = Protocol.AWARD_TASK
    PERFORMATIVES = (Pf.FAILURE,)

    case_id: str
    reason: str


@dataclass
class AmbulanceCall:
    """P10 (cfp): pedido de ambulância.

    Attributes:
        case_id (str): Caso (thread).
        priority (str): P1 ou P2.
        cell (int): Célula do caso.
        reply_by (float): Prazo das propostas.
    """

    PROTOCOL = Protocol.REQUEST_AMBULANCE
    PERFORMATIVES = (Pf.CFP,)

    case_id: str
    priority: str
    cell: int
    reply_by: float


@dataclass
class AmbulanceProposal:
    """P10 (propose): proposta de uma ambulância livre.

    Attributes:
        case_id (str): Caso.
        eta_s (float): Tempo estimado até ao centro da célula, com o atraso de ativação.
    """

    PROTOCOL = Protocol.REQUEST_AMBULANCE
    PERFORMATIVES = (Pf.PROPOSE,)

    case_id: str
    eta_s: float


@dataclass
class AmbulanceRefusal:
    """P10 (refuse): a ambulância não está disponível.

    Attributes:
        case_id (str): Caso.
        reason (str): busy ou out_of_service.
    """

    PROTOCOL = Protocol.REQUEST_AMBULANCE
    PERFORMATIVES = (Pf.REFUSE,)

    case_id: str
    reason: str


@dataclass
class AmbulanceAward:
    """P10 (accept-proposal): adjudicação da ambulância, com a localização exata.

    Attributes:
        case_id (str): Caso.
        priority (str): P1 ou P2.
        location (list): Localização exata do doente, [x, y].
    """

    PROTOCOL = Protocol.REQUEST_AMBULANCE
    PERFORMATIVES = (Pf.ACCEPT_PROPOSAL,)

    case_id: str
    priority: str
    location: list


@dataclass
class AmbulanceRejection:
    """P10 (reject-proposal): outra ambulância ganhou.

    Attributes:
        case_id (str): Caso.
    """

    PROTOCOL = Protocol.REQUEST_AMBULANCE
    PERFORMATIVES = (Pf.REJECT_PROPOSAL,)

    case_id: str


@dataclass
class AmbulanceConfirmation:
    """P10 (inform): a ambulância compromete-se com o caso.

    Attributes:
        case_id (str): Caso.
    """

    PROTOCOL = Protocol.REQUEST_AMBULANCE
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str


@dataclass
class AmbulanceFailure:
    """P10 (failure): a ambulância ficou ocupada depois de propor.

    Attributes:
        case_id (str): Caso.
        reason (str): busy.
    """

    PROTOCOL = Protocol.REQUEST_AMBULANCE
    PERFORMATIVES = (Pf.FAILURE,)

    case_id: str
    reason: str

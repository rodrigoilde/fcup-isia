"""Mensagens da resposta no terreno (sub-organização SO-DR): protocolos P11 a P14 e P20.

Reserva e recolha do DAE, estados dos intervenientes, dispensa e fecho do caso. As convenções são
as de `messages_detection`.
"""

from dataclasses import dataclass, field

from .ontology import Performative as Pf
from .ontology import Protocol


@dataclass
class AEDReservationRequest:
    """P11 (request): reserva de um DAE para um caso.

    Attributes:
        case_id (str): Caso (thread).
        aed_id (int): DAE a reservar.
        valid_for_s (float): Validade pedida (T_code).
        priority (str): Prioridade do caso.
        award_token (str): Token que o estafeta vai apresentar na recolha.
    """

    PROTOCOL = Protocol.RESERVE_AED
    PERFORMATIVES = (Pf.REQUEST,)

    case_id: str
    aed_id: int
    valid_for_s: float
    priority: str
    award_token: str


@dataclass
class AEDReservation:
    """P11 (agree): reserva aceite (OS3: uma reserva ativa por DAE).

    Attributes:
        case_id (str): Caso.
        aed_id (int): DAE reservado.
        reservation_ref (str): Referência a apresentar na recolha.
        expires_at (float): Fim da validade da reserva.
    """

    PROTOCOL = Protocol.RESERVE_AED
    PERFORMATIVES = (Pf.AGREE,)

    case_id: str
    aed_id: int
    reservation_ref: str
    expires_at: float


@dataclass
class AEDReservationRefusal:
    """P11 (refuse): o DAE não pode ser reservado.

    Attributes:
        case_id (str): Caso.
        aed_id (int): DAE.
        reason (str): reserved, in_use ou unavailable.
    """

    PROTOCOL = Protocol.RESERVE_AED
    PERFORMATIVES = (Pf.REFUSE,)

    case_id: str
    aed_id: int
    reason: str


@dataclass
class AEDReservationCancel:
    """P11 (cancel): o caso já não precisa da reserva.

    Attributes:
        case_id (str): Caso.
        aed_id (int): DAE.
        reservation_ref (str): Reserva a cancelar.
    """

    PROTOCOL = Protocol.RESERVE_AED
    PERFORMATIVES = (Pf.CANCEL,)

    case_id: str
    aed_id: int
    reservation_ref: str


@dataclass
class AEDRetrieval:
    """P12 (request): o estafeta pede a abertura do armário.

    Attributes:
        case_id (str): Caso (thread).
        aed_id (int): DAE a desbloquear.
        reservation_ref (str): Referência da reserva recebida na adjudicação.
        award_token (str): Prova da adjudicação.
    """

    PROTOCOL = Protocol.RETRIEVE_AED
    PERFORMATIVES = (Pf.REQUEST,)

    case_id: str
    aed_id: int
    reservation_ref: str
    award_token: str


@dataclass
class AEDUnlock:
    """P12 (inform): código de abertura.

    Attributes:
        case_id (str): Caso.
        aed_id (int): DAE.
        access_code (str): Código de uso único.
    """

    PROTOCOL = Protocol.RETRIEVE_AED
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    aed_id: int
    access_code: str


@dataclass
class AEDRetrievalFailure:
    """P12 (failure): o armário não abre ou o DAE não está lá.

    Attributes:
        case_id (str): Caso.
        aed_id (int): DAE.
        reason (str): missing_or_faulty, invalid_reservation ou expired.
    """

    PROTOCOL = Protocol.RETRIEVE_AED
    PERFORMATIVES = (Pf.FAILURE,)

    case_id: str
    aed_id: int
    reason: str


@dataclass
class StatusReport:
    """P13: mudança de estado de um voluntário, testemunha ou ambulância.

    Attributes:
        case_id (str): Caso (thread).
        status (str): Um dos ResponderStatus (EN_ROUTE, ON_SCENE, EMS_TOOK_OVER, ...).
        t_status (float): Quando o estado mudou.
        eta_s (float | None): ETA restante, em EN_ROUTE.
        detail (dict): Dados próprios do estado, por exemplo {real_incident: bool} em CLINICAL_CONFIRMATION.
    """

    PROTOCOL = Protocol.STATUS_UPDATE
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    status: str
    t_status: float
    eta_s: float | None = None
    detail: dict = field(default_factory=dict)


@dataclass
class OnSceneRoster:
    """P13: resposta do coordenador ao ON_SCENE da ambulância: quem está no local para a passagem (P19).

    Attributes:
        case_id (str): Caso.
        responders (list): Pseudónimos dos voluntários (ou guias) no local.
    """

    PROTOCOL = Protocol.STATUS_UPDATE
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    responders: list = field(default_factory=list)


@dataclass
class Release:
    """P14 (cancel): dispensa de um voluntário ou de uma ambulância.

    Attributes:
        case_id (str): Caso.
        reason (str): enough_on_scene, false_alarm, ems_took_over ou case_closed.
    """

    PROTOCOL = Protocol.RELEASE_RESPONDER
    PERFORMATIVES = (Pf.CANCEL,)

    case_id: str
    reason: str


@dataclass
class ReleaseAck:
    """P14 (inform): o voluntário está outra vez disponível.

    Attributes:
        case_id (str): Caso.
    """

    PROTOCOL = Protocol.RELEASE_RESPONDER
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str


@dataclass
class CaseClosure:
    """P20: fecho do caso.

    Attributes:
        case_id (str): Caso.
        outcome (str): FALSE_ALARM, RESOLVED_ON_SCENE, TRANSPORTED ou TIMEOUT.
        t_closed (float): Instante do fecho; os dados pessoais têm de ser apagados até t_closed + T_ret (OS11).
    """

    PROTOCOL = Protocol.CLOSE_CASE
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    outcome: str
    t_closed: float


@dataclass
class AEDRelease:
    """P20: aviso de fecho ao guardião de um DAE reservado para o caso.

    Attributes:
        case_id (str): Caso.
        aed_id (int): DAE.
        reservation_ref (str): Reserva libertada.
    """

    PROTOCOL = Protocol.CLOSE_CASE
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    aed_id: int
    reservation_ref: str

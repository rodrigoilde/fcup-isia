"""Mensagens da assistência no local (sub-organização SO-AT): protocolos P15 a P19.

O P16 e o P17 trocam-se entre a app de orientação e o ajudante no mesmo telemóvel, por isso nunca
passam pela rede (F13); ficam no registo de auditoria como mensagens locais. As convenções são as
de `messages_detection`.
"""

from dataclasses import dataclass

from .ontology import Performative as Pf
from .ontology import Protocol


@dataclass
class HelpEnRoute:
    """P15: diz aos guias no local que ajuda vem a caminho (só ETA, nunca identidades).

    Attributes:
        case_id (str): Caso.
        eta_responder_s (float | None): ETA do primeiro voluntário.
        eta_aed_s (float | None): ETA do DAE.
        eta_ems_s (float | None): ETA da ambulância.
    """

    PROTOCOL = Protocol.HELP_EN_ROUTE_NOTICE
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    eta_responder_s: float | None = None
    eta_aed_s: float | None = None
    eta_ems_s: float | None = None


@dataclass
class Instruction:
    """P16 (local): um passo do protocolo de orientação dado ao ajudante.

    Attributes:
        case_id (str): Caso.
        step (str): Passo do guidanceProtocol (OS12).
        text (str): Instrução curta.
        cadence_per_min (int | None): Metrónomo das compressões.
        expected_s (float): Duração esperada do passo.
    """

    PROTOCOL = Protocol.GIVE_INSTRUCTION
    PERFORMATIVES = (Pf.REQUEST,)

    case_id: str
    step: str
    text: str
    cadence_per_min: int | None = None
    expected_s: float = 0.0


@dataclass
class Feedback:
    """P17 (local): o que o ajudante fez ou observou.

    Attributes:
        case_id (str): Caso.
        result (str): DONE, CANNOT, NO_RESPONSE, BREATHING, NOT_BREATHING, WOKE_UP ou TIRED.
        t_feedback (float): Quando o ajudante respondeu.
    """

    PROTOCOL = Protocol.REPORT_FEEDBACK
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    result: str
    t_feedback: float


@dataclass
class TakeoverRequest:
    """P18 (request): um voluntário chegou e assume o lugar da testemunha guiada.

    Attributes:
        case_id (str): Caso.
        arriving_role (str): Papel de quem chega (nunca a identidade).
    """

    PROTOCOL = Protocol.TAKEOVER_FROM_BYSTANDER
    PERFORMATIVES = (Pf.REQUEST,)

    case_id: str
    arriving_role: str


@dataclass
class ActionSummary:
    """P18 (inform): o que a testemunha já fez.

    Attributes:
        case_id (str): Caso.
        cpr_started_at (float | None): Quando começaram as compressões.
    """

    PROTOCOL = Protocol.TAKEOVER_FROM_BYSTANDER
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    cpr_started_at: float | None = None


@dataclass
class HandoverRequest:
    """P19 (request): a ambulância pede o resumo a quem está no local.

    Attributes:
        case_id (str): Caso.
    """

    PROTOCOL = Protocol.HANDOVER_TO_EMS
    PERFORMATIVES = (Pf.REQUEST,)

    case_id: str


@dataclass
class HandoverSummary:
    """P19 (inform): resumo clínico para a equipa da ambulância (só vai para a EMS, OS5).

    Attributes:
        case_id (str): Caso.
        collapse_estimate_t (float | None): Instante estimado do colapso.
        cpr_start_t (float | None): Quando começou a RCP.
        shocks (int): Choques dados.
        first_shock_t (float | None): Instante do primeiro choque.
        current_state (str): Descrição curta do estado do doente.
    """

    PROTOCOL = Protocol.HANDOVER_TO_EMS
    PERFORMATIVES = (Pf.INFORM,)

    case_id: str
    collapse_estimate_t: float | None = None
    cpr_start_t: float | None = None
    shocks: int = 0
    first_shock_t: float | None = None
    current_state: str = ""

"""Política de divulgação do papel PrivacyGuardian (decisão D7, regras OS5 e OS11).

Princípio da necessidade de saber:

- localização exata e acesso ao edifício: só o coordenador do caso (um hub) e a ambulância,
  enquanto o caso está ativo, com consentimento do titular ou, em P1/P2 com o titular incapaz de
  consentir, com base nos interesses vitais (RGPD, art. 9.º, n.º 2, alínea c));
- dados clínicos e identidade: só a ambulância do caso.

O coordenador só reencaminha a localização dentro das adjudicações P09/P10.
Desenho em docs/03-detailed-design.md §4.3.
"""

from dataclasses import dataclass

from ..protocol.ontology import DisclosureField

VITAL_PRIORITIES = {"P1", "P2"}
LOCATION_FIELDS = {DisclosureField.PRECISE_LOCATION, DisclosureField.BUILDING_ACCESS}
EMS_ONLY_FIELDS = {DisclosureField.CLINICAL, DisclosureField.IDENTITY}


@dataclass(frozen=True)
class DisclosureDecision:
    """Resultado de um pedido de divulgação P24.

    Attributes:
        granted (bool): Se o dado é divulgado.
        reason (str): Base legal ("consent", "vital_interests") ou motivo da recusa.
    """

    granted: bool
    reason: str


def coarse_area(pos, spacing_m: float) -> list[float]:
    """Localização grosseira de um alerta: a posição arredondada ao cruzamento mais próximo da grelha.

    Com a grelha de 100 m da cidade, o hub fica a saber a zona (~100 m) em vez da posição exata.
    Chega para separar doentes diferentes na mesma célula (revisão da D7).

    Args:
        pos: Posição [x, y] em metros.
        spacing_m (float): Distância entre cruzamentos da grelha.

    Returns:
        list[float]: O cruzamento mais próximo, [x, y].
    """
    return [round(pos[0] / spacing_m) * spacing_m, round(pos[1] / spacing_m) * spacing_m]


def may_receive(field_name: str, requester_kind: str) -> bool:
    """Indica se um tipo de agente precisa de saber um campo (OS5)."""
    if field_name in EMS_ONLY_FIELDS:
        return requester_kind == "ems"
    if field_name in LOCATION_FIELDS:
        return requester_kind in ("hub", "ems")
    return False


def decide_disclosure(field_name: str, requester_kind: str, priority: str,
                      case_active: bool = True, consent: bool = False) -> DisclosureDecision:
    """Decide um pedido de divulgação P24.

    Args:
        field_name (str): Campo pedido (precise_location, building_access, clinical, identity).
        requester_kind (str): Tipo de agente que pede ("hub", "ems", "volunteer", ...).
        priority (str): Prioridade do caso.
        case_active (bool): Se o caso ainda está aberto.
        consent (bool): Se o titular consentiu.

    Returns:
        DisclosureDecision: A decisão e a sua justificação, que fica no registo de auditoria.
    """
    if not case_active:
        return DisclosureDecision(False, "case_not_active")
    if field_name not in LOCATION_FIELDS and field_name not in EMS_ONLY_FIELDS:
        return DisclosureDecision(False, "unknown_field")
    if not may_receive(field_name, requester_kind):
        return DisclosureDecision(False, "not_need_to_know")
    if consent:
        return DisclosureDecision(True, "consent")
    if priority in VITAL_PRIORITIES:
        return DisclosureDecision(True, "vital_interests")
    return DisclosureDecision(False, "no_legal_basis")

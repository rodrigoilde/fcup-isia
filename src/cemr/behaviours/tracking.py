"""Acompanhamento das adjudicações pelo papel IncidentCoordinator (regras OL6 e OL8).

OL6: uma adjudicação que falha, ou que passa de ETA + δ sem chegar, deixa de cobrir a sua tarefa e
leva a novo recrutamento. OL8: com N_need socorristas no local, dispensam-se os que ainda vêm a
caminho. Lógica pura, sem SPADE nem mensagens: os estados do caso (`agents/case_track.py` e
`agents/case_awards.py`) chamam estas funções e tratam do envio e do registo.
Desenho em docs/03-detailed-design.md §4.2.
"""

from dataclasses import dataclass

from ..protocol.ontology import TaskType


@dataclass
class AwardInfo:
    """Uma adjudicação a um voluntário.

    Attributes:
        task (str): GO_TO_PATIENT ou FETCH_AED.
        eta_s (float): ETA da proposta.
        aed_id (int | None): DAE a ir buscar.
        status (str): awarded, committed, failed ou released.
        arrive_by (float): ETA + δ; depois disto a adjudicação está em risco (OL6).
        on_scene_t (float | None): Quando chegou ao local.
        late (bool): Se passou de `arrive_by` sem chegar.
        aed_delivered (bool): Se entregou o DAE.
    """

    task: str
    eta_s: float
    aed_id: int | None = None
    status: str = "awarded"
    arrive_by: float = 0.0
    on_scene_t: float | None = None
    late: bool = False
    aed_delivered: bool = False

    @property
    def active(self) -> bool:
        """Se a adjudicação ainda conta (não falhou nem foi dispensada)."""
        return self.status in ("awarded", "committed")


def late_awards(awards: dict[str, AwardInfo], now: float) -> list[str]:
    """Voluntários que passaram agora de ETA + δ sem chegar (OL6); os já marcados não contam.

    Args:
        awards (dict[str, AwardInfo]): Adjudicações do caso, por voluntário.
        now (float): Instante simulado atual.

    Returns:
        list[str]: Voluntários a marcar como atrasados.
    """
    late = []
    for name, info in awards.items():
        if info.active and info.on_scene_t is None and not info.late and now > info.arrive_by:
            late.append(name)
    return late


def uncovered_tasks(needs: dict, awards: dict[str, AwardInfo]) -> dict:
    """Tarefas ainda em falta (OL6): uma adjudicação falhada, ou atrasada sem ter chegado, não cobre.

    Depois de um DAE entregue, a tarefa FETCH_AED deixa de fazer falta.

    Args:
        needs (dict): Tarefa -> número de voluntários pedidos.
        awards (dict[str, AwardInfo]): Adjudicações do caso, por voluntário.

    Returns:
        dict: Tarefa -> quantos voluntários faltam (só as tarefas com falta).
    """
    aed_delivered = any(a.aed_delivered for a in awards.values())
    missing = {}
    for task, wanted in needs.items():
        if task == TaskType.FETCH_AED and aed_delivered:
            continue
        covering = [a for a in awards.values()
                    if a.task == task and a.active and (a.on_scene_t is not None or not a.late)]
        if wanted > len(covering):
            missing[task] = wanted - len(covering)
    return missing


def enough_on_scene(awards: dict[str, AwardInfo], n_need: int) -> bool:
    """Se já há N_need voluntários adjudicados no local (OL8)."""
    on_scene = sum(1 for a in awards.values() if a.on_scene_t is not None and a.active)
    return on_scene >= n_need


def surplus_awards(awards: dict[str, AwardInfo]) -> list[str]:
    """Voluntários a dispensar quando já há gente suficiente no local (OL8).

    São os que ainda vêm a caminho. O estafeta do DAE só é dispensado depois de algum DAE entregue,
    porque a desfibrilhação continua a fazer falta.

    Args:
        awards (dict[str, AwardInfo]): Adjudicações do caso, por voluntário.

    Returns:
        list[str]: Voluntários a dispensar.
    """
    aed_done = any(a.aed_delivered for a in awards.values())
    surplus = []
    for name, info in awards.items():
        if info.active and info.on_scene_t is None and (info.task != TaskType.FETCH_AED or aed_done):
            surplus.append(name)
    return surplus

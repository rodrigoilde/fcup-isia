"""Estado CLOSE do caso (papel IncidentCoordinator): fecho (P20) e rótulos para a reputação (P21).

O fecho vai para todos os participantes e, duas vezes, para o guardião do titular, que apaga os
dados (OS11). Os rótulos de resultado são escritos uma vez por caso fechado (OL9) e juntados à
tabela de confiança do hub. Desenho em docs/03-detailed-design.md §4.5.
"""

from typing import TYPE_CHECKING

from ..protocol.messages_hubs import OutcomeLabels
from ..protocol.messages_response import AEDRelease, CaseClosure
from ..protocol.ontology import CaseState
from ..sim.directory import Directory
from .case_track import release_all
from .conversation import Step

if TYPE_CHECKING:
    from .case_fsm import CaseFSM


def outcome_labels(fsm: "CaseFSM") -> list[dict]:
    """Rótulos de resultado (P21).

    A referência é a confirmação clínica da ambulância; um falso alarme confirmado por um humano
    (portador ou testemunha) também conta. Os voluntários são avaliados por chegarem dentro de ETA + δ.
    """
    case = fsm.case
    real = None
    if case.clinical is not None:
        real = bool(case.clinical.get("real_incident"))
    elif case.human_false_alarm:
        real = False
    labels = []
    if real is not None:
        for src in case.sources.values():
            if src.positive:
                labels.append({"pseudonym": src.name, "kind": "source", "success": real})
    for name, info in case.awards.items():
        if info.on_scene_t is not None:
            labels.append({"pseudonym": name, "kind": "responder", "success": info.on_scene_t <= info.arrive_by})
        elif info.status == "failed" or info.late:
            labels.append({"pseudonym": name, "kind": "responder", "success": False})
    return labels


class Close(Step):
    """Fecha o caso: dispensa, avisa os participantes e os guardiões (OS11) e rotula o resultado (P21)."""

    async def step(self) -> None:
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        case.state = CaseState.CLOSED
        await release_all(fsm, "case_closed")
        closure = CaseClosure(case.case_id, str(case.outcome), fsm.now())
        recipients = set(case.awards) | set(case.guides) | case.disclosers
        if case.ems:
            recipients.add(case.ems)
        if case.subject:
            recipients.add(case.subject)
        for name in sorted(recipients):
            await fsm.send(name, closure)
        if case.subject:                          # o guardião apaga os dados no fecho (OS11): vai duas vezes
            await fsm.send(case.subject, closure)
        res = case.reservation
        if res and res.get("ref"):
            await fsm.send(Directory.hub(res["aed_id"]), AEDRelease(case.case_id, res["aed_id"], res["ref"]))
        fsm.log("case_closed", outcome=str(case.outcome), priority=str(case.priority),
                duration=round(fsm.now() - case.t_open, 1))
        labels = outcome_labels(fsm)
        hub.log_local(OutcomeLabels(case.case_id, labels), "ReputationManager", case.case_id)     # P21 (OL9)
        hub.apply_outcome(case.case_id, labels)
        await fsm.replicate(closed=True)

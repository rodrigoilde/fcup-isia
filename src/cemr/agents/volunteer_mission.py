"""Missão de um voluntário depois de uma adjudicação, nos papéis VolunteerResponder e AEDRunner.

    FETCH_AED:      GO_AED -> RETRIEVE -> GO_SCENE -> ON_SCENE
    GO_TO_PATIENT:                        GO_SCENE -> ON_SCENE

Em qualquer estado, uma dispensa (P14) ou o fecho do caso (P20) terminam a missão, e um takeover
(P28) muda o coordenador. Desenho em docs/03-detailed-design.md §2.5.
"""

from typing import TYPE_CHECKING

from ..protocol.messages_assistance import ActionSummary, HandoverRequest, HandoverSummary, TakeoverRequest
from ..protocol.messages_dispatch import Award
from ..protocol.messages_hubs import Takeover
from ..protocol.messages_response import (AEDRetrieval, AEDRetrievalFailure, AEDUnlock, CaseClosure, Release,
                                          ReleaseAck, StatusReport)
from ..protocol.ontology import ResponderStatus, TaskType
from ..sim.directory import Directory
from .conversation import Conversation, Incoming, Step

if TYPE_CHECKING:
    from .volunteer import VolunteerAgent

GO_AED, RETRIEVE, GO_SCENE, ON_SCENE = "GO_AED", "RETRIEVE", "GO_SCENE", "ON_SCENE"
HOUR_S = 3600


class Mission(Conversation):
    """Compromisso de um voluntário com um caso.

    Attributes:
        award (Award): A adjudicação.
        coordinator (str): Hub que coordena o caso (muda num takeover P28).
        no_show (str | None): "withdraw", "silent" ou None (modelo A6).
        slowdown (float): Fator entre a viagem real e a estimada.
        has_aed (bool): Se já levantou o DAE.
        ended (bool): Se a missão foi interrompida (dispensa ou fecho).
    """

    def __init__(self, agent: "VolunteerAgent", award: Award, coordinator: str, thread: str,
                 no_show: str | None = None, slowdown: float = 1.0):
        super().__init__({thread})
        self.volunteer = agent
        self.award = award
        self.coordinator = coordinator
        self.thread = thread
        self.no_show = no_show
        self.slowdown = slowdown
        self.withdraw_at = None
        if no_show == "withdraw":
            self.withdraw_at = agent.now() + agent.uniform(agent.cfg["volunteers"]["withdraw_after_s"])
        self.has_aed = False
        self.ended = False
        self.took_over = False
        fetch = award.task == TaskType.FETCH_AED
        self.add_state(GO_AED, GoToAED(self), initial=fetch)
        self.add_state(RETRIEVE, Retrieve(self))
        self.add_state(GO_SCENE, GoToScene(self), initial=not fetch)
        self.add_state(ON_SCENE, OnScene(self))
        self.add_transition(GO_AED, RETRIEVE)
        self.add_transition(RETRIEVE, GO_SCENE)
        self.add_transition(GO_SCENE, ON_SCENE)

    async def status(self, status: str, **fields) -> None:
        """Envia um estado ao coordenador (P13)."""
        v = self.volunteer
        report = StatusReport(self.award.case_id, status, v.now(), **fields)
        await v.send_to(self.coordinator, report, thread=self.thread)

    async def interrupted(self, inc: Incoming) -> bool:
        """Trata dispensa (P14), fecho (P20) e takeover (P28); devolve True se a missão acaba."""
        v = self.volunteer
        p = inc.payload
        if isinstance(p, Takeover):
            self.coordinator = p.new_coordinator
            v.log("coordinator_changed", case=self.award.case_id, coordinator=self.coordinator)
            return False
        if isinstance(p, Release):
            await v.reply(inc, ReleaseAck(self.award.case_id))
            v.log("released", case=self.award.case_id, reason=p.reason)
            self.ended = True
            return True
        if isinstance(p, CaseClosure):
            self.ended = True
            return True
        return False

    async def travel(self, dest) -> bool:
        """Desloca-se até `dest`; devolve False se foi dispensado, desistiu ou nunca se mexeu."""
        v = self.volunteer
        if self.no_show == "silent":                  # fechou a app: não se mexe nem responde
            await self.wait_until_released()
            return False
        mode = {"speed": v.travel_mode["speed"] / self.slowdown,
                "overhead_s": v.travel_mode.get("overhead_s", 0) * self.slowdown}
        arrival = v.world.start_move(v.label, tuple(dest), mode)
        await self.status(ResponderStatus.EN_ROUTE, eta_s=round(arrival - v.now(), 1))
        while v.now() < arrival:
            until = arrival
            if self.withdraw_at:
                until = min(arrival, self.withdraw_at)
            inc = await self.next_incoming(until)
            if inc is not None and await self.interrupted(inc):
                return False
            if self.withdraw_at and v.now() >= self.withdraw_at:
                await self.status(ResponderStatus.WITHDRAWN, detail={"reason": "cannot_continue"})
                v.log("withdrew", case=self.award.case_id)
                return False
        return True

    async def wait_until_released(self) -> None:
        """Um voluntário que não aparece só reage à dispensa ou ao fecho do caso."""
        v = self.volunteer
        while not self.ended:
            inc = await self.next_incoming(v.now() + HOUR_S)
            if inc is not None and await self.interrupted(inc):
                return

    async def take_over_from_bystander(self) -> None:
        """P18: substitui a testemunha guiada sem interromper as compressões."""
        if self.award.guide and not self.took_over:
            self.took_over = True
            request = TakeoverRequest(self.award.case_id, "VolunteerResponder")
            await self.volunteer.send_to(self.award.guide, request, thread=self.thread)

    async def finished(self) -> None:
        await self.volunteer.mission_finished(self)


class GoToAED(Step):
    """Vai ao armário do DAE reservado."""

    async def step(self) -> None:
        m = self.fsm
        if await m.travel(m.volunteer.world.aed_registry[m.award.aed_id]["pos"]):
            await m.status(ResponderStatus.AT_AED)
            self.set_next_state(RETRIEVE)


class Retrieve(Step):
    """Levanta o DAE (P12); sem DAE, o estafeta vai na mesma ajudar na RCP."""

    async def step(self) -> None:
        m, v = self.fsm, self.fsm.volunteer
        a = m.award
        await v.send_to(Directory.hub(a.aed_id), AEDRetrieval(a.case_id, a.aed_id, a.reservation_ref, a.award_token),
                        thread=m.thread)
        until = v.now() + v.cfg["volunteers"]["aed_answer_timeout_s"]
        result = None
        while result is None and v.now() < until:
            inc = await m.next_incoming(until)
            if inc is None:
                continue
            if await m.interrupted(inc):
                return
            if isinstance(inc.payload, (AEDUnlock, AEDRetrievalFailure)):
                result = inc.payload
        if isinstance(result, AEDUnlock):
            await v.sleep(v.cfg["volunteers"]["aed_retrieval_s"])
            m.has_aed = True
            await m.status(ResponderStatus.AED_OK)
        elif isinstance(result, AEDRetrievalFailure):
            await m.status(ResponderStatus.AED_MISSING, detail={"reason": result.reason})
        else:
            await m.status(ResponderStatus.AED_MISSING, detail={"reason": "no_answer"})
        self.set_next_state(GO_SCENE)


class GoToScene(Step):
    """Vai ao local do doente."""

    async def step(self) -> None:
        m = self.fsm
        if await m.travel(m.award.location):
            await m.status(ResponderStatus.ON_SCENE)
            self.set_next_state(ON_SCENE)


class OnScene(Step):
    """No local: coloca o DAE, substitui a testemunha, faz RCP e passa o caso à ambulância (P19)."""

    async def step(self) -> None:
        m, v = self.fsm, self.fsm.volunteer
        loc = m.award.location
        if m.has_aed:
            result = v.world.act_attach_aed(loc, v.label)
            if result["attached"]:
                await m.status(ResponderStatus.AED_DELIVERED)
            if result["shock"]:
                await m.status(ResponderStatus.SHOCK_DELIVERED)
        await m.take_over_from_bystander()                               # P18
        if v.world.act_start_cpr(loc, v.label):                          # _PerformBLS
            await m.status(ResponderStatus.CPR_STARTED)
        until = v.now() + v.cfg["volunteers"]["max_on_scene_s"]         # caso a dispensa se tenha perdido (F5)
        while v.now() < until:
            inc = await m.next_incoming(until)
            if inc is None:
                continue
            if await m.interrupted(inc):
                return
            if isinstance(inc.payload, ActionSummary):
                v.log("took_over", case=m.award.case_id, guide=inc.sender, cpr_started_at=inc.payload.cpr_started_at)
            if isinstance(inc.payload, HandoverRequest):                # P19
                await v.reply(inc, self.handover_summary())

    def handover_summary(self) -> HandoverSummary:
        """Resumo para a equipa da ambulância."""
        m, v = self.fsm, self.fsm.volunteer
        patient = v.world.patient_at(m.award.location)
        if patient is None:
            return HandoverSummary(m.award.case_id, None, None, 0, None, "no patient found")
        state = "CPR in progress" if patient.needs_cpr else "stable"
        return HandoverSummary(m.award.case_id, None, patient.cpr_start_t, patient.shocks, patient.first_shock_t, state)

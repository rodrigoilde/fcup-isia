"""EMSAgent: an ambulance (EMSUnit, R8).

Bids in the P10 Contract Net with its ETA, travels when awarded, takes over care on scene (P19
handover with a volunteer, if one is there) and reports the clinical confirmation that serves as the
reference label for reputation (P13 CLINICAL_CONFIRMATION).

    EMSMission: TRAVEL -> ON_SCENE -> RETURN
"""

from ..protocol.messages import (AmbulanceAward, AmbulanceCall, AmbulanceConfirmation, AmbulanceFailure,
                                 AmbulanceProposal, AmbulanceRefusal, AmbulanceRejection, CaseClosure,
                                 HandoverRequest, HandoverSummary, OnSceneRoster, Release, ReleaseAck, StatusReport,
                                 Takeover)
from ..protocol.ontology import EMSState, ResponderStatus
from ..sim.directory import Directory
from .base import CEMRAgent, Conversation, Incoming, Step

TRAVEL, ON_SCENE, RETURN = "TRAVEL", "ON_SCENE", "RETURN"


class EMSAgent(CEMRAgent):
    KIND = "ems"

    def __init__(self, idx: int, ctx, base):
        super().__init__(Directory.ems(idx), ctx, base)

    async def on_setup(self):
        self.state = EMSState.AVAILABLE
        self.case: str | None = None

    async def on_message(self, inc: Incoming) -> None:
        p = inc.payload
        if isinstance(p, AmbulanceCall):
            if self.state != EMSState.AVAILABLE:
                await self.reply(inc, AmbulanceRefusal(p.case_id, "busy"))
                return
            eta = self.cfg["ems"]["dispatch_delay_s"] + self.world.grid.travel_time(
                self.pos(), self.world.grid.centroid(p.cell), self.cfg["travel"]["ambulance"])
            await self.reply(inc, AmbulanceProposal(p.case_id, round(eta, 1)))
        elif isinstance(p, AmbulanceAward):
            if self.state != EMSState.AVAILABLE:
                await self.reply(inc, AmbulanceFailure(p.case_id, "busy"))
                return
            self.state, self.case = EMSState.EN_ROUTE, p.case_id
            await self.reply(inc, AmbulanceConfirmation(p.case_id))
            self.log("ems_committed", case=p.case_id)
            self.open_conversation(EMSMission(self, p, inc.sender, inc.thread))
        elif isinstance(p, (AmbulanceRejection, CaseClosure, Release, Takeover)):
            pass
        else:
            await super().on_message(inc)


class EMSMission(Conversation):
    def __init__(self, unit: EMSAgent, award: AmbulanceAward, coordinator: str, thread: str):
        super().__init__({thread})
        self.unit = unit
        self.award = award
        self.coordinator = coordinator
        self.thread = thread
        self.real_incident = False
        self.closed = False
        self.add_state(TRAVEL, Travel(self), initial=True)
        self.add_state(ON_SCENE, OnScene(self))
        self.add_state(RETURN, Return(self))
        self.add_transition(TRAVEL, ON_SCENE)
        self.add_transition(TRAVEL, RETURN)
        self.add_transition(ON_SCENE, RETURN)

    async def status(self, status: str, **kw) -> None:
        await self.unit.send_to(self.coordinator, StatusReport(self.award.case_id, status, self.unit.now(), **kw),
                                thread=self.thread)

    async def wait_for(self, payload_type, seconds: float):
        until = self.unit.now() + seconds
        while self.unit.now() < until:
            inc = await self.next_incoming(until)
            if inc is None:
                continue
            if isinstance(inc.payload, Takeover):                      # P28: new coordinator
                self.coordinator = inc.payload.new_coordinator
                continue
            if isinstance(inc.payload, Release):                       # P14: human-confirmed false alarm (OS6)
                await self.unit.reply(inc, ReleaseAck(self.award.case_id))
                self.unit.log("ems_released", case=self.award.case_id, reason=inc.payload.reason)
                self.closed = True
                return None
            if isinstance(inc.payload, CaseClosure):
                self.closed = True
                return None
            if isinstance(inc.payload, payload_type):
                return inc
        return None

    async def finished(self) -> None:
        self.unit.state, self.unit.case = EMSState.AVAILABLE, None


class Travel(Step):
    async def step(self):
        m, u = self.fsm, self.fsm.unit
        arrival = u.world.start_move(u.label, tuple(m.award.location), u.cfg["travel"]["ambulance"],
                                     delay_s=u.cfg["ems"]["dispatch_delay_s"])
        await m.status(ResponderStatus.EN_ROUTE, eta_s=round(arrival - u.now(), 1))
        await m.wait_for(type(None), arrival - u.now())       # until arrival, or the case is closed
        self.set_next_state(RETURN if m.closed else ON_SCENE)


class OnScene(Step):
    async def step(self):
        m, u = self.fsm, self.fsm.unit
        u.state = EMSState.ON_SCENE
        m.real_incident = u.world.act_ems_arrive(tuple(m.award.location), u.label)
        await m.status(ResponderStatus.ON_SCENE)
        if m.real_incident:
            roster = await m.wait_for(OnSceneRoster, 10)
            if roster is not None and roster.payload.responders:
                volunteer = roster.payload.responders[0]
                await u.send_to(volunteer, HandoverRequest(m.award.case_id), thread=m.thread)     # P19
                summary = await m.wait_for(HandoverSummary, 20)
                u.log("handover", case=m.award.case_id, volunteer=volunteer, received=summary is not None)
            await m.status(ResponderStatus.EMS_TOOK_OVER)
            await m.wait_for(type(None), u.cfg["ems"]["care_on_scene_s"])   # care, still listening (P28)
        await m.status(ResponderStatus.CLINICAL_CONFIRMATION, detail={"real_incident": m.real_incident})
        if m.real_incident:
            await m.status(ResponderStatus.TRANSPORTING)
            u.state = EMSState.TRANSPORT
        self.set_next_state(RETURN)


class Return(Step):
    async def step(self):
        m, u = self.fsm, self.fsm.unit
        if m.real_incident:
            await u.sleep(u.cfg["ems"]["transport_s"])
            u.world.teleport(u.label, u.home)
        else:
            arrival = u.world.start_move(u.label, u.home, u.cfg["travel"]["ambulance"])
            await u.sleep(arrival - u.now())
        u.log("ems_available")

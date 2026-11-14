"""EMSAgent: uma ambulância (papel EMSUnit, R8).

Propõe-se no Contract Net do P10 com o seu ETA, desloca-se quando é adjudicada, assume o doente no
local (passagem P19 com um voluntário, se houver) e reporta a confirmação clínica, que serve de
rótulo de referência para a reputação (P13 CLINICAL_CONFIRMATION).

    EMSMission: TRAVEL -> ON_SCENE -> RETURN

Desenho em docs/03-detailed-design.md §2.5.
"""

from ..protocol.messages_assistance import HandoverRequest, HandoverSummary
from ..protocol.messages_dispatch import (AmbulanceAward, AmbulanceCall, AmbulanceConfirmation, AmbulanceFailure,
                                          AmbulanceProposal, AmbulanceRefusal, AmbulanceRejection)
from ..protocol.messages_hubs import Takeover
from ..protocol.messages_response import CaseClosure, OnSceneRoster, Release, ReleaseAck, StatusReport
from ..protocol.ontology import EMSState, ResponderStatus
from ..sim.directory import Directory
from .base import CEMRAgent
from .conversation import Conversation, Incoming, Step

TRAVEL, ON_SCENE, RETURN = "TRAVEL", "ON_SCENE", "RETURN"


class EMSAgent(CEMRAgent):
    """Ambulância: agente baseado em utilidade, que se propõe pelo ETA.

    Attributes:
        state (EMSState): Estado da ambulância.
        case (str | None): Caso a que está adjudicada.
    """

    KIND = "ems"

    def __init__(self, idx: int, ctx, base):
        super().__init__(Directory.ems(idx), ctx, base)

    async def on_setup(self) -> None:
        self.state = EMSState.AVAILABLE
        self.case: str | None = None

    async def on_message(self, inc: Incoming) -> None:
        p = inc.payload
        if isinstance(p, AmbulanceCall):
            await self.on_call(inc, p)
        elif isinstance(p, AmbulanceAward):
            await self.on_award(inc, p)
        elif isinstance(p, (AmbulanceRejection, CaseClosure, Release, Takeover)):
            pass
        else:
            await super().on_message(inc)

    async def on_call(self, inc: Incoming, call: AmbulanceCall) -> None:
        """P10 (cfp): propõe o ETA até ao centro da célula, se estiver livre."""
        if self.state != EMSState.AVAILABLE:
            await self.reply(inc, AmbulanceRefusal(call.case_id, "busy"))
            return
        grid = self.world.grid
        travel = grid.travel_time(self.pos(), grid.centroid(call.cell), self.cfg["travel"]["ambulance"])
        eta = self.cfg["ems"]["dispatch_delay_s"] + travel
        await self.reply(inc, AmbulanceProposal(call.case_id, round(eta, 1)))

    async def on_award(self, inc: Incoming, award: AmbulanceAward) -> None:
        """P10 (accept-proposal): compromete-se com o caso, se ainda estiver livre."""
        if self.state != EMSState.AVAILABLE:
            await self.reply(inc, AmbulanceFailure(award.case_id, "busy"))
            return
        self.state = EMSState.EN_ROUTE
        self.case = award.case_id
        await self.reply(inc, AmbulanceConfirmation(award.case_id))
        self.log("ems_committed", case=award.case_id)
        self.open_conversation(EMSMission(self, award, inc.sender, inc.thread))


class EMSMission(Conversation):
    """Missão de uma ambulância num caso.

    Attributes:
        award (AmbulanceAward): A adjudicação.
        coordinator (str): Hub que coordena o caso (muda num takeover P28).
        real_incident (bool): Se encontrou um doente no local.
        closed (bool): Se o caso foi fechado ou a ambulância dispensada antes de chegar.
    """

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

    async def status(self, status: str, **fields) -> None:
        """Envia um estado ao coordenador (P13)."""
        u = self.unit
        report = StatusReport(self.award.case_id, status, u.now(), **fields)
        await u.send_to(self.coordinator, report, thread=self.thread)

    async def wait_for(self, payload_type, seconds: float) -> Incoming | None:
        """Espera até `seconds` por uma mensagem do tipo dado, tratando entretanto P14, P20 e P28.

        Returns:
            Incoming | None: A mensagem, ou None se o tempo acabou ou o caso foi fechado.
        """
        u = self.unit
        until = u.now() + seconds
        while u.now() < until:
            inc = await self.next_incoming(until)
            if inc is None:
                continue
            p = inc.payload
            if isinstance(p, Takeover):                             # P28: novo coordenador
                self.coordinator = p.new_coordinator
            elif isinstance(p, Release):                            # P14: falso alarme confirmado por um humano (OS6)
                await u.reply(inc, ReleaseAck(self.award.case_id))
                u.log("ems_released", case=self.award.case_id, reason=p.reason)
                self.closed = True
                return None
            elif isinstance(p, CaseClosure):
                self.closed = True
                return None
            elif payload_type is not None and isinstance(p, payload_type):
                return inc
        return None

    async def finished(self) -> None:
        self.unit.state = EMSState.AVAILABLE
        self.unit.case = None


class Travel(Step):
    """A caminho do local, ainda a ouvir o coordenador."""

    async def step(self) -> None:
        m, u = self.fsm, self.fsm.unit
        arrival = u.world.start_move(u.label, tuple(m.award.location), u.cfg["travel"]["ambulance"],
                                     delay_s=u.cfg["ems"]["dispatch_delay_s"])
        await m.status(ResponderStatus.EN_ROUTE, eta_s=round(arrival - u.now(), 1))
        await m.wait_for(None, arrival - u.now())               # até chegar, ou até o caso fechar
        self.set_next_state(RETURN if m.closed else ON_SCENE)


class OnScene(Step):
    """No local: recebe a passagem (P19), assume o doente e confirma se o incidente era real."""

    async def step(self) -> None:
        m, u = self.fsm, self.fsm.unit
        ecfg = u.cfg["ems"]
        u.state = EMSState.ON_SCENE
        m.real_incident = u.world.act_ems_arrive(tuple(m.award.location), u.label)
        await m.status(ResponderStatus.ON_SCENE)
        if m.real_incident:
            roster = await m.wait_for(OnSceneRoster, ecfg["roster_wait_s"])
            if roster is not None and roster.payload.responders:
                volunteer = roster.payload.responders[0]
                await u.send_to(volunteer, HandoverRequest(m.award.case_id), thread=m.thread)
                summary = await m.wait_for(HandoverSummary, ecfg["handover_wait_s"])
                u.log("handover", case=m.award.case_id, volunteer=volunteer, received=summary is not None)
            await m.status(ResponderStatus.EMS_TOOK_OVER)
            await m.wait_for(None, ecfg["care_on_scene_s"])     # assistência no local, ainda a ouvir (P28)
        await m.status(ResponderStatus.CLINICAL_CONFIRMATION, detail={"real_incident": m.real_incident})
        if m.real_incident:
            await m.status(ResponderStatus.TRANSPORTING)
            u.state = EMSState.TRANSPORT
        self.set_next_state(RETURN)


class Return(Step):
    """Transporte para o hospital ou regresso à base, até ficar outra vez disponível."""

    async def step(self) -> None:
        u = self.fsm.unit
        if self.fsm.real_incident:
            await u.sleep(u.cfg["ems"]["transport_s"])
            u.world.teleport(u.label, u.home)
        else:
            arrival = u.world.start_move(u.label, u.home, u.cfg["travel"]["ambulance"])
            await u.sleep(arrival - u.now())
        u.log("ems_available")

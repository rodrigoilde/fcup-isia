"""VolunteerAgent: VolunteerResponder (R5) and AEDRunner (R6), depending on the awarded task.

The volunteer evaluates each call on its own phone (_EvaluateAlertLocally): its position never
leaves the device, only the ETA does (D3). After an award it runs a Mission FSM:

    FETCH_AED:      GO_AED -> RETRIEVE -> GO_SCENE -> ON_SCENE
    GO_TO_PATIENT:                        GO_SCENE -> ON_SCENE

OS2: at most one active commitment. OS8: calls beyond A_max alerts per hour or K_max recent awards
are refused by the app without disturbing the volunteer ("alert_shown" counts the ones that reach them).

Behaviour model (A6): with probability p_no_show an awarded volunteer either withdraws on the way
(WITHDRAWN) or silently never shows up; real travel takes 0–30 % longer than the estimate. These make
OL6 (re-recruitment) and OL8 (release of surplus) matter.
"""

from collections import deque

from ..protocol.messages import (ActionSummary, AEDRetrieval, AEDRetrievalFailure, AEDUnlock, Award,
                                 AwardConfirmation, AwardFailure, AwardRejection, CallForProposals, CaseClosure,
                                 HandoverRequest, HandoverSummary, Proposal, ProposalRefusal, RegistrationAck, Release,
                                 ReleaseAck, StatusReport, Takeover, TakeoverRequest)
from ..protocol.ontology import Qualification, RegistrationRole, ResponderStatus, TaskType
from ..sim.directory import Directory
from ..sim.incidents import VolunteerProfile
from .base import CEMRAgent, Conversation, Incoming, Step

GO_AED, RETRIEVE, GO_SCENE, ON_SCENE = "GO_AED", "RETRIEVE", "GO_SCENE", "ON_SCENE"


class VolunteerAgent(CEMRAgent):
    KIND = "volunteer"

    def __init__(self, idx: int, ctx, profile: VolunteerProfile):
        super().__init__(Directory.volunteer(idx), ctx, profile.pos)
        self.mode = profile.mode
        self.qualification = profile.qualification

    async def on_setup(self):
        self.commitment: str | None = None
        self.alert_times: deque[float] = deque()
        self.award_times: deque[float] = deque()
        await self.register_with_hubs(RegistrationRole.VOLUNTEER, self.qualification)

    @property
    def travel_mode(self) -> dict:
        return self.cfg["travel"][self.mode]

    async def on_message(self, inc: Incoming) -> None:
        p = inc.payload
        if isinstance(p, CallForProposals):
            self.spawn(lambda: self.evaluate_call(inc), "evaluate_call")
        elif isinstance(p, Award):
            await self.on_award(inc, p)
        elif isinstance(p, (AwardRejection, RegistrationAck, CaseClosure, Release, Takeover, ActionSummary)):
            pass
        else:
            await super().on_message(inc)

    def _load_reason(self) -> str | None:
        vcfg = self.cfg["volunteers"]
        now = self.now()
        while self.alert_times and now - self.alert_times[0] > 3600:
            self.alert_times.popleft()
        while self.award_times and now - self.award_times[0] > 7200:
            self.award_times.popleft()
        if len(self.alert_times) >= vcfg["max_alerts_per_hour"]:
            return "load_cap"
        if len(self.award_times) >= vcfg["max_consecutive_awards"]:
            return "load_cap"
        return None

    async def evaluate_call(self, inc: Incoming) -> None:
        """_EvaluateAlertLocally: decide and compute ETAs on the phone; only the ETA is sent."""
        cfp: CallForProposals = inc.payload
        await self.sleep(self.uniform(self.cfg["volunteers"]["eval_delay_s"]))
        reason = "busy" if self.commitment else self._load_reason()
        if reason != "load_cap":
            self.alert_times.append(self.now())
            self.log("alert_shown", case=cfp.case_id)                      # reaches the human (OS8)
        if reason is None and self.rng.random() >= self.cfg["volunteers"]["p_accept"]:
            reason = "declined"
        offers = [] if reason else self.compute_offers(cfp)
        if reason is None and not offers:
            reason = "unqualified"
        if reason:
            await self.reply(inc, ProposalRefusal(cfp.case_id, reason))
            return
        await self.reply(inc, Proposal(cfp.case_id, offers, self.qualification))

    def compute_offers(self, cfp: CallForProposals) -> list[dict]:
        grid = self.world.grid
        here = self.pos()
        target = grid.centroid(cfp.cell)
        offers = []
        if (TaskType.GO_TO_PATIENT in cfp.tasks
                and Qualification(self.qualification).rank >= Qualification(cfp.min_qualification).rank):
            offers.append({"task": TaskType.GO_TO_PATIENT.value,
                           "eta_s": round(grid.travel_time(here, target, self.travel_mode), 1)})
        if TaskType.FETCH_AED in cfp.tasks and cfp.candidate_aeds:
            retrieval = self.cfg["volunteers"]["aed_retrieval_s"]
            best = min(cfp.candidate_aeds, key=lambda a: grid.travel_time(here, tuple(a["pos"]), self.travel_mode)
                       + grid.travel_time(tuple(a["pos"]), target, self.travel_mode))
            eta = (grid.travel_time(here, tuple(best["pos"]), self.travel_mode) + retrieval
                   + grid.travel_time(tuple(best["pos"]), target, self.travel_mode))
            offers.append({"task": TaskType.FETCH_AED.value, "eta_s": round(eta, 1), "aed_id": best["aed_id"]})
        return offers

    async def on_award(self, inc: Incoming, award: Award) -> None:
        if self.commitment is not None:                                  # OS2
            await self.reply(inc, AwardFailure(award.case_id, "busy"))
            return
        self.commitment = award.case_id
        self.award_times.append(self.now())
        await self.reply(inc, AwardConfirmation(award.case_id, award.task))
        vcfg = self.cfg["volunteers"]
        no_show = None
        if self.rng.random() < vcfg["p_no_show"]:
            no_show = "withdraw" if self.rng.random() < 0.5 else "silent"
        slowdown = self.uniform(vcfg["speed_variability"])
        self.log("committed", case=award.case_id, task=award.task, no_show=no_show)
        self.open_conversation(Mission(self, award, inc.sender, inc.thread, no_show, slowdown))

    async def mission_finished(self, mission: "Mission") -> None:
        self.commitment = None
        self.world.teleport(self.label, self.pos())                     # stop wherever we are
        self.log("mission_end", case=mission.award.case_id)
        await self.register_with_hubs(RegistrationRole.VOLUNTEER, self.qualification)


class Mission(Conversation):
    def __init__(self, agent: VolunteerAgent, award: Award, coordinator: str, thread: str,
                 no_show: str | None = None, slowdown: float = 1.0):
        super().__init__({thread})
        self.volunteer = agent
        self.award = award
        self.coordinator = coordinator
        self.thread = thread
        self.no_show = no_show
        self.slowdown = slowdown
        self.withdraw_at = agent.now() + agent.uniform((30, 120)) if no_show == "withdraw" else None
        self.has_aed = False
        self.ended = False
        self.took_over = False
        fetch = award.task == TaskType.FETCH_AED
        self.add_state(GO_AED, GoToAED(self), initial=fetch)
        self.add_state(RETRIEVE, Retrieve(self))
        self.add_state(GO_SCENE, GoToScene(self), initial=not fetch)
        self.add_state(ON_SCENE, OnScene(self))
        for src, dst in ((GO_AED, RETRIEVE), (RETRIEVE, GO_SCENE), (GO_SCENE, ON_SCENE)):
            self.add_transition(src, dst)

    async def status(self, status: str, **kw) -> None:
        await self.volunteer.send_to(self.coordinator, StatusReport(self.award.case_id, status, self.volunteer.now(),
                                                                    **kw), thread=self.thread)

    async def interrupted(self, inc: Incoming) -> bool:
        """Release (P14) or closure (P20) ends the mission at any point; a takeover (P28) changes who
        coordinates the case."""
        if isinstance(inc.payload, Takeover):
            self.coordinator = inc.payload.new_coordinator
            self.volunteer.log("coordinator_changed", case=self.award.case_id, coordinator=self.coordinator)
            return False
        if isinstance(inc.payload, Release):
            await self.volunteer.reply(inc, ReleaseAck(self.award.case_id))
            self.volunteer.log("released", case=self.award.case_id, reason=inc.payload.reason)
            self.ended = True
            return True
        if isinstance(inc.payload, CaseClosure):
            self.ended = True
            return True
        return False

    async def travel(self, dest) -> bool:
        """Move to dest; False if released, withdrawn or silently absent."""
        v = self.volunteer
        if self.no_show == "silent":                 # app closed: never moves, never reports
            while not self.ended:
                inc = await self.next_incoming(v.now() + 3600)
                if inc is not None and await self.interrupted(inc):
                    return False
            return False
        mode = {"speed": v.travel_mode["speed"] / self.slowdown,
                "overhead_s": v.travel_mode.get("overhead_s", 0) * self.slowdown}
        arrival = v.world.start_move(v.label, tuple(dest), mode)
        await self.status(ResponderStatus.EN_ROUTE, eta_s=round(arrival - v.now(), 1))
        while v.now() < arrival:
            until = min(arrival, self.withdraw_at) if self.withdraw_at else arrival
            inc = await self.next_incoming(until)
            if inc is not None and await self.interrupted(inc):
                return False
            if self.withdraw_at and v.now() >= self.withdraw_at:
                await self.status(ResponderStatus.WITHDRAWN, detail={"reason": "cannot_continue"})
                v.log("withdrew", case=self.award.case_id)
                return False
        return True

    async def take_over_from_bystander(self) -> None:
        """P18: relieve the guided witness without interrupting compressions."""
        if self.award.guide and not self.took_over:
            self.took_over = True
            await self.volunteer.send_to(self.award.guide, TakeoverRequest(self.award.case_id, "VolunteerResponder"),
                                         thread=self.thread)

    async def finished(self) -> None:
        await self.volunteer.mission_finished(self)


class GoToAED(Step):
    async def step(self):
        m = self.fsm
        if await m.travel(m.volunteer.world.aed_registry[m.award.aed_id]["pos"]):
            await m.status(ResponderStatus.AT_AED)
            self.set_next_state(RETRIEVE)


class Retrieve(Step):
    async def step(self):
        m, v = self.fsm, self.fsm.volunteer
        a = m.award
        await v.send_to(Directory.hub(a.aed_id), AEDRetrieval(a.case_id, a.aed_id, a.reservation_ref, a.award_token),
                        thread=m.thread)
        until = v.now() + 20
        while v.now() < until:
            inc = await m.next_incoming(until)
            if inc is None:
                continue
            if await m.interrupted(inc):
                return
            if isinstance(inc.payload, AEDUnlock):
                await v.sleep(v.cfg["volunteers"]["aed_retrieval_s"])
                m.has_aed = True
                await m.status(ResponderStatus.AED_OK)
                break
            if isinstance(inc.payload, AEDRetrievalFailure):
                await m.status(ResponderStatus.AED_MISSING, detail={"reason": inc.payload.reason})
                break
        else:
            await m.status(ResponderStatus.AED_MISSING, detail={"reason": "no_answer"})
        self.set_next_state(GO_SCENE)       # without an AED the runner still helps with CPR


class GoToScene(Step):
    async def step(self):
        m = self.fsm
        if await m.travel(m.award.location):
            await m.status(ResponderStatus.ON_SCENE)
            self.set_next_state(ON_SCENE)


class OnScene(Step):
    async def step(self):
        m, v = self.fsm, self.fsm.volunteer
        loc = m.award.location
        if m.has_aed:
            result = v.world.act_attach_aed(loc, v.label)
            if result["attached"]:
                await m.status(ResponderStatus.AED_DELIVERED)
            if result["shock"]:
                await m.status(ResponderStatus.SHOCK_DELIVERED)
        await m.take_over_from_bystander()                                # P18
        if v.world.act_start_cpr(loc, v.label):                           # _PerformBLS
            await m.status(ResponderStatus.CPR_STARTED)
        until = v.now() + v.cfg["volunteers"]["max_on_scene_s"]          # in case the release was lost (F5)
        while v.now() < until:
            inc = await m.next_incoming(until)
            if inc is None:
                continue
            if await m.interrupted(inc):
                return
            if isinstance(inc.payload, ActionSummary):
                v.log("took_over", case=m.award.case_id, guide=inc.sender,
                      cpr_started_at=inc.payload.cpr_started_at)
            if isinstance(inc.payload, HandoverRequest):                 # P19
                patient = v.world.patient_at(loc)
                await v.reply(inc, HandoverSummary(
                    m.award.case_id, None,
                    patient.cpr_start_t if patient else None, patient.shocks if patient else 0,
                    patient.first_shock_t if patient else None,
                    "no patient found" if patient is None else "CPR in progress" if patient.needs_cpr else "stable"))

"""BystanderAgent: a citizen's phone. Plays four roles:

- WitnessReporter (R2): reports a collapse (P01), corroborates (P03), answers triage (P04);
- BystanderGuide (R9): the app's step-by-step BLS guidance, started by P05;
- OnSceneHelper (R10): the human who follows the instructions (behaviour model, A5);
- PrivacyGuardian (R12): of the witness's own location, which marks where the patient is.

The guide and the helper share the phone, so P16 GiveInstruction and P17 ReportFeedback never cross
the network: guidance keeps going without coverage (F13). They are still logged as protocol messages.

    BYSTANDERGUIDE = (Assist)^ω
    Assist = ActivateGuidance . (Coach+ || HelpEnRouteNotice*) . [TakeoverFromBystander | HandoverToEMS] . CloseCase
    Coach  = _SelectNextStep . GiveInstruction . (ReportFeedback | _DetectSilence . StatusUpdate)
    ONSCENEHELPER = (GiveInstruction . _PerformInstruction . _ObservePatient . [ReportFeedback])+ . [TakeoverFromBystander]
"""

import asyncio
import itertools

from spade.behaviour import CyclicBehaviour
from spade.message import Message

from ..behaviours import guidance as gp
from ..behaviours.privacy import decide_disclosure
from ..protocol.messages import (ActionSummary, AlertAck, AlertReport, CaseClosure, CorroborationQuery,
                                 CorroborationReply, Disclosure, DisclosureRefusal, DisclosureRequest, Feedback,
                                 GuidanceAck, GuidanceActivation, HandoverRequest, HandoverSummary, HelpEnRoute,
                                 Instruction, RegistrationAck, StatusReport, Takeover, TakeoverRequest, TriageAnswer,
                                 TriageQuestion, encode)
from ..protocol.ontology import (Answer, EventType, PromptStatus, RegistrationRole, ResponderStatus, SensorPolicy,
                                 SourceKind, TriageQuestionId, Verdict)
from ..sim.directory import Directory
from .base import CEMRAgent, Conversation, Incoming, Step

REPORT_CONFIDENCE = 0.8
SCENE_MEMORY_S = 900


class Watching(CyclicBehaviour):
    """_ObserveScene: what the citizen sees, delivered by the environment."""

    async def run(self):
        queue = self.agent.world.perceptions(self.agent.label)
        try:
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return
        if event["type"] == "observe_collapse":
            await self.agent.on_collapse_seen(event)


class BystanderAgent(CEMRAgent):
    KIND = "bystander"

    def __init__(self, idx: int, ctx, pos):
        super().__init__(Directory.bystander(idx), ctx, pos)

    async def on_setup(self):
        self._alert_ids = itertools.count(1)
        self.scene: tuple | None = None
        self.scene_t = 0.0
        self.scene_cell: int | None = None
        self.active_cases: dict[str, str] = {}
        self.guidance: "Guidance | None" = None
        self.service_handlers = {DisclosureRequest: self.on_disclosure_request}
        self.add_worker_behaviour(Watching())
        await self.register_with_hubs(RegistrationRole.WITNESS)

    def at_scene(self) -> bool:
        return self.scene is not None and self.now() - self.scene_t <= SCENE_MEMORY_S

    async def on_collapse_seen(self, event: dict) -> None:
        self.scene, self.scene_t = tuple(self.pos()), self.now()       # standing next to the patient
        self.scene_cell = self.world.grid.cell_of(self.scene)
        self.log("witnessing", cell=self.scene_cell)
        await self.register_with_hubs(RegistrationRole.WITNESS)        # reachable by the scene's hub
        will_report = event.get("will_report")              # scripted incidents may fix the decision
        if will_report or (will_report is None and self.rng.random() < self.cfg["witness"]["p_report"]):
            self.spawn(self.report, "witness_report")

    async def report(self) -> None:
        await self.sleep(self.uniform(self.cfg["witness"]["report_delay_s"]))
        alert_id = f"{self.label}-a{next(self._alert_ids)}"
        report = AlertReport(alert_id, SourceKind.WITNESS, EventType.WITNESS_COLLAPSE, REPORT_CONFIDENCE,
                             self.scene_cell, self.now(), SensorPolicy.HUMAN, PromptStatus.NOT_APPLICABLE)
        await self.raise_alert(report, self.scene_cell)

    async def on_message(self, inc: Incoming) -> None:
        p = inc.payload
        if isinstance(p, CorroborationQuery):
            seen = self.at_scene() and self.scene_cell == p.cell and p.window_from <= self.scene_t <= p.window_to
            await self.reply(inc, CorroborationReply(p.candidate_id, Verdict.CONFIRM if seen else Verdict.NO_DATA,
                                                     REPORT_CONFIDENCE if seen else 0.0))
        elif isinstance(p, TriageQuestion):
            self.spawn(lambda: self.answer(inc, p), "triage_answer")
        elif isinstance(p, GuidanceActivation):
            await self.on_guidance_activation(inc, p)
        elif isinstance(p, CaseClosure):
            if self.active_cases.pop(p.case_id, None) is not None:
                self.log("purge", case=p.case_id)                       # _PurgeCaseData (OS11)
        elif isinstance(p, (AlertAck, RegistrationAck, HelpEnRoute, TakeoverRequest, Takeover)):
            pass
        else:
            await super().on_message(inc)

    async def answer(self, inc: Incoming, q: TriageQuestion) -> None:
        wcfg = self.cfg["witness"]
        await self.sleep(self.uniform(wcfg["answer_delay_s"]))
        if self.rng.random() >= wcfg["p_answer"]:
            return                                                       # silence counts as "unknown"
        answer = Answer.UNKNOWN
        if self.at_scene():
            seen = self.world.observe_patient(self.scene, self.rng, wcfg["observation_error"])
            if q.question == TriageQuestionId.SCENE_SAFE:
                answer = Answer.YES
            elif q.question == TriageQuestionId.CALLED_112:
                answer = Answer.YES if self.rng.random() < wcfg["p_called_112"] else Answer.NO
            elif seen is not None:
                value = seen["responsive"] if q.question == TriageQuestionId.RESPONSIVE else seen["breathing_normally"]
                answer = Answer.YES if value else Answer.NO
        await self.reply(inc, TriageAnswer(q.candidate_id, q.question, answer, self.now()))

    # --- P05: guidance ---------------------------------------------------------------------------
    async def on_guidance_activation(self, inc: Incoming, act: GuidanceActivation) -> None:
        accepted = self.at_scene() and self.guidance is None
        await self.reply(inc, GuidanceAck(act.candidate_id, accepted),
                         performative="agree" if accepted else "refuse")
        if accepted:
            self.guidance = Guidance(self, act, inc.sender, inc.thread)
            self.open_conversation(self.guidance)
            self.spawn(self.guidance.helper.run, "on_scene_helper")
            self.log("guidance_started", case=act.candidate_id, priority=act.priority)

    async def on_disclosure_request(self, inc: Incoming) -> None:
        """PrivacyGuardian of the witness's own location: it marks where the patient is."""
        req: DisclosureRequest = inc.payload
        decision = decide_disclosure(req.field_name, Directory.kind_of(inc.sender), req.priority)
        granted = decision.granted and self.at_scene()
        reason = decision.reason if not decision.granted or granted else "not_at_scene"
        self.log("disclosure", case=req.case_id, field=req.field_name, to=inc.sender, granted=granted, reason=reason)
        if granted:
            if req.case_id not in self.active_cases:
                self.spawn(lambda case=req.case_id: self.purge_later(case), "purge_fallback")
            self.active_cases[req.case_id] = req.priority
            await self.reply(inc, Disclosure(req.case_id, req.field_name, [round(c, 1) for c in self.scene]))
        else:
            await self.reply(inc, DisclosureRefusal(req.case_id, req.field_name, reason))


class Helper:
    """OnSceneHelper (R10): the lay rescuer following the app. Behaviour model (A5): may give up, gets tired."""

    def __init__(self, agent: BystanderAgent, guidance: "Guidance"):
        self.agent = agent
        self.guidance = guidance
        self.instructions: asyncio.Queue = asyncio.Queue()
        self.gave_up = False
        self.cycles = 0
        self.cpr_started_at: float | None = None

    async def run(self) -> None:
        a = self.agent
        wcfg = a.cfg["witness"]
        while True:
            instruction = await self.instructions.get()
            if instruction is None:
                return
            if self.gave_up:
                continue                                                 # silence: the guide will notice
            await a.sleep(a.uniform(wcfg["react_delay_s"]))
            give_up = wcfg["p_give_up"] + wcfg["p_give_up_per_cycle"] * max(0, self.cycles - 2)
            if a.rng.random() < give_up:
                self.gave_up = True
                a.log("helper_gave_up", case=self.guidance.case_id, step=instruction.step)
                continue
            result = await self.perform(instruction)
            if result is not None:
                feedback = Feedback(instruction.case_id, result, a.now())
                a.log_local(feedback, "BystanderGuide", self.guidance.thread)            # P17 (local)
                await self.guidance.enqueue(self.guidance.local_message(feedback))

    async def perform(self, instruction: Instruction) -> str | None:
        """_PerformInstruction and _ObservePatient."""
        a = self.agent
        seen = a.world.observe_patient(a.scene, a.rng, a.cfg["witness"]["observation_error"]) or \
            {"responsive": True, "breathing_normally": True}
        if instruction.step == "CHECK_RESPONSE":
            return gp.WOKE_UP if seen["responsive"] else gp.NO_RESPONSE
        if instruction.step == "CHECK_BREATHING":
            return gp.BREATHING if seen["breathing_normally"] else gp.NOT_BREATHING
        if instruction.step == "COMPRESSIONS":
            if a.world.act_start_cpr(a.scene, a.label) and self.cpr_started_at is None:
                self.cpr_started_at = a.now()
            self.cycles += 1
            await a.sleep(instruction.expected_s)                        # one cycle of compressions
            return gp.TIRED if self.cycles >= a.cfg["witness"]["tired_after_cycles"] else gp.DONE
        if instruction.step == "KEEP_WATCHING":
            await a.sleep(instruction.expected_s)
            return gp.NOT_BREATHING if not seen["breathing_normally"] else gp.DONE
        return gp.DONE


class Guidance(Conversation):
    """BystanderGuide (R9) for one case. One state loop: select a step, instruct, wait for feedback."""

    def __init__(self, agent: BystanderAgent, act: GuidanceActivation, coordinator: str, thread: str):
        super().__init__({thread})
        self.witness = agent
        self.case_id = act.candidate_id
        self.coordinator = coordinator
        self.thread = thread
        self.state_ = gp.GuideState.from_triage(act.triage)
        self.helper = Helper(agent, self)
        self.add_state("GUIDE", Guide(self), initial=True)

    def local_message(self, payload) -> Message:
        a = self.witness
        return Message(to=str(a.jid), sender=str(a.jid), thread=self.thread, body=encode(payload),
                       metadata={"performative": str(payload.PERFORMATIVES[0]), "protocol": payload.PROTOCOL.value})

    async def finished(self) -> None:
        self.helper.instructions.put_nowait(None)
        self.witness.guidance = None
        self.witness.log("guidance_ended", case=self.case_id)


class Guide(Step):
    async def step(self):
        g, a = self.fsm, self.agent
        t_silence = a.cfg["witness"]["t_silence_s"]
        silent_reported = False
        while True:
            step = gp.next_step(g.state_)                                # _SelectNextStep (OS12)
            instruction = Instruction(g.case_id, step.id, step.text, step.cadence_per_min, step.expected_s)
            a.log_local(instruction, "OnSceneHelper", g.thread)        # P16 (local)
            g.helper.instructions.put_nowait(instruction)
            deadline = a.now() + step.expected_s + t_silence
            repeats = 0
            while True:
                inc = await g.next_incoming(deadline)
                if inc is None:                                          # _DetectSilence
                    if repeats == 0:
                        repeats += 1
                        g.helper.instructions.put_nowait(instruction)  # repeat the instruction once
                        deadline = a.now() + step.expected_s + t_silence
                        continue
                    if not silent_reported:
                        silent_reported = True
                        await a.send_to(g.coordinator, StatusReport(g.case_id, ResponderStatus.WITNESS_SILENT,
                                                                    a.now()), thread=g.thread)
                    deadline = a.now() + 3600
                    continue
                p = inc.payload
                if isinstance(p, Feedback):
                    g.state_.apply(step.id, p.result)
                    break
                if isinstance(p, HelpEnRoute):                           # P15: adapt the instructions
                    a.log("help_en_route_received", case=g.case_id, eta_responder=p.eta_responder_s,
                          eta_aed=p.eta_aed_s, eta_ems=p.eta_ems_s)
                elif isinstance(p, Takeover):
                    g.coordinator = p.new_coordinator
                elif isinstance(p, TakeoverRequest):                     # P18: a volunteer arrived
                    await a.reply(inc, self.summary())
                    a.log("handed_over", case=g.case_id, to=inc.sender, role=p.arriving_role)
                    return
                elif isinstance(p, HandoverRequest):                     # P19 with no volunteer on scene
                    patient = a.world.patient_at(a.scene)
                    await a.reply(inc, HandoverSummary(g.case_id, a.scene_t, g.helper.cpr_started_at,
                                                       patient.shocks if patient else 0,
                                                       patient.first_shock_t if patient else None,
                                                       "guided bystander CPR" if g.helper.cpr_started_at else ""))
                    a.log("handed_over", case=g.case_id, to=inc.sender, role="EMSUnit")
                    return
                elif isinstance(p, CaseClosure):
                    if a.active_cases.pop(p.case_id, None) is not None:
                        a.log("purge", case=p.case_id)                   # OS11
                    return

    def summary(self) -> ActionSummary:
        g = self.fsm
        return ActionSummary(g.case_id, g.helper.cpr_started_at, 0, None, 0)

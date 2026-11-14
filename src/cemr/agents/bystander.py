"""BystanderAgent: o telemóvel de um cidadão. Tem quatro papéis:

- WitnessReporter (R2): reporta um colapso (P01), corrobora (P03) e responde à triagem (P04);
- BystanderGuide (R9): a orientação passo a passo da app, ligada pelo P05;
- OnSceneHelper (R10): a pessoa que segue as instruções (modelo de comportamento, A5);
- PrivacyGuardian (R12): da sua própria localização, que indica onde está o doente.

A app e o ajudante partilham o telemóvel, por isso o P16 GiveInstruction e o P17 ReportFeedback
nunca passam pela rede: a orientação continua sem cobertura (F13). Ficam registados como mensagens
locais. Liveness:

    BYSTANDERGUIDE = (Assist)^ω
    Assist = ActivateGuidance . (Coach+ || HelpEnRouteNotice*) . [TakeoverFromBystander | HandoverToEMS] . CloseCase
    Coach  = _SelectNextStep . GiveInstruction . (ReportFeedback | _DetectSilence . StatusUpdate)

A app e o ajudante estão em `bystander_guide`. Desenho em docs/03-detailed-design.md §2.6.
"""

import asyncio
import itertools

from spade.behaviour import CyclicBehaviour

from ..behaviours.privacy import coarse_area, decide_disclosure
from ..protocol.messages_assistance import HelpEnRoute, TakeoverRequest
from ..protocol.messages_detection import (AlertAck, AlertReport, CorroborationQuery, CorroborationReply, GuidanceAck,
                                           GuidanceActivation, TriageAnswer, TriageQuestion)
from ..protocol.messages_hubs import Disclosure, DisclosureRefusal, DisclosureRequest, RegistrationAck, Takeover
from ..protocol.messages_response import CaseClosure
from ..protocol.ontology import (Answer, EventType, PromptStatus, RegistrationRole, SensorPolicy, SourceKind,
                                 TriageQuestionId, Verdict)
from ..sim.directory import Directory
from .base import CEMRAgent
from .bystander_guide import Guidance
from .conversation import NEVER, Incoming


class Watching(CyclicBehaviour):
    """_ObserveScene: o que o cidadão vê, entregue pelo ambiente."""

    async def run(self) -> None:
        queue = self.agent.world.perceptions(self.agent.label)
        try:
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return
        if event["type"] == "observe_collapse":
            await self.agent.on_collapse_seen(event)


class BystanderAgent(CEMRAgent):
    """Telemóvel de um cidadão com a app de orientação e o modelo do ajudante humano.

    O comportamento está em camadas, como numa arquitetura híbrida: o cansaço e a desistência do
    ajudante sobrepõem-se à instrução corrente da app.

    Attributes:
        scene (tuple | None): Onde o cidadão viu o colapso (está ao lado do doente).
        scene_t (float): Quando o viu.
        scene_cell (int | None): Célula do local.
        scene_area (list | None): Área do local (~100 m), que vai nos alertas.
        guidance (Guidance | None): Orientação em curso, se houver.
    """

    KIND = "bystander"

    def __init__(self, idx: int, ctx, pos):
        super().__init__(Directory.bystander(idx), ctx, pos)

    async def on_setup(self) -> None:
        self.alert_ids = itertools.count(1)
        self.scene: tuple | None = None
        self.scene_t = 0.0
        self.scene_cell: int | None = None
        self.scene_area: list | None = None
        self.guidance: Guidance | None = None
        self.service_handlers = {DisclosureRequest: self.on_disclosure_request}
        self.add_behaviour(Watching(), NEVER)
        await self.register_with_hubs(RegistrationRole.WITNESS)

    def at_scene(self) -> bool:
        """Se o cidadão ainda está no local de um colapso que viu."""
        if self.scene is None:
            return False
        return self.now() - self.scene_t <= self.cfg["witness"]["scene_memory_s"]

    async def on_collapse_seen(self, event: dict) -> None:
        """Viu alguém cair: regista-se no hub do local e talvez reporte (P01)."""
        self.scene = tuple(self.pos())
        self.scene_t = self.now()
        self.scene_cell = self.world.grid.cell_of(self.scene)
        self.scene_area = coarse_area(self.scene, self.cfg["city"]["grid_spacing_m"])
        self.log("witnessing", cell=self.scene_cell)
        await self.register_with_hubs(RegistrationRole.WITNESS)       # contactável pelo hub do local
        will_report = event.get("will_report")                         # o guião pode fixar a decisão
        if will_report is None:
            will_report = self.rng.random() < self.cfg["witness"]["p_report"]
        if will_report:
            self.spawn(self.report, "witness_report")

    async def report(self) -> None:
        """Envia o relato da testemunha (P01), depois do atraso de reação."""
        wcfg = self.cfg["witness"]
        await self.sleep(self.uniform(wcfg["report_delay_s"]))
        alert_id = f"{self.label}-a{next(self.alert_ids)}"
        report = AlertReport(alert_id, SourceKind.WITNESS, EventType.WITNESS_COLLAPSE, wcfg["report_confidence"],
                             self.scene_cell, self.scene_area, self.now(), SensorPolicy.HUMAN,
                             PromptStatus.NOT_APPLICABLE)
        await self.raise_alert(report, self.scene_cell)

    async def on_message(self, inc: Incoming) -> None:
        p = inc.payload
        if isinstance(p, CorroborationQuery):
            await self.corroborate(inc, p)
        elif isinstance(p, TriageQuestion):
            self.spawn(lambda: self.answer(inc, p), "triage_answer")
        elif isinstance(p, GuidanceActivation):
            await self.on_guidance_activation(inc, p)
        elif isinstance(p, CaseClosure):
            self.purge(p.case_id)                                       # _PurgeCaseData (OS11)
        elif isinstance(p, (AlertAck, RegistrationAck, HelpEnRoute, TakeoverRequest, Takeover)):
            pass
        else:
            await super().on_message(inc)

    async def corroborate(self, inc: Incoming, query: CorroborationQuery) -> None:
        """P03: confirma se viu um colapso na célula e na janela de tempo pedidas."""
        seen = (self.at_scene() and self.scene_cell == query.cell
                and query.window_from <= self.scene_t <= query.window_to)
        if seen:
            confidence = self.cfg["witness"]["report_confidence"]
            reply = CorroborationReply(query.candidate_id, Verdict.CONFIRM, confidence, self.scene_area)
        else:
            reply = CorroborationReply(query.candidate_id, Verdict.NO_DATA, 0.0)
        await self.reply(inc, reply)

    async def answer(self, inc: Incoming, question: TriageQuestion) -> None:
        """P04: responde a uma pergunta da triagem pelo que vê, com erro de observação."""
        wcfg = self.cfg["witness"]
        await self.sleep(self.uniform(wcfg["answer_delay_s"]))
        if self.rng.random() >= wcfg["p_answer"]:
            return                                                       # o silêncio conta como "unknown"
        answer = Answer.UNKNOWN
        if self.at_scene():
            seen = self.world.observe_patient(self.scene, self.rng, wcfg["observation_error"])
            if question.question == TriageQuestionId.SCENE_SAFE:
                answer = Answer.YES
            elif question.question == TriageQuestionId.CALLED_112:
                answer = Answer.YES if self.rng.random() < wcfg["p_called_112"] else Answer.NO
            elif seen is not None:
                key = "responsive" if question.question == TriageQuestionId.RESPONSIVE else "breathing_normally"
                answer = Answer.YES if seen[key] else Answer.NO
        await self.reply(inc, TriageAnswer(question.candidate_id, question.question, answer, self.now()))

    async def on_guidance_activation(self, inc: Incoming, act: GuidanceActivation) -> None:
        """P05: liga a orientação se o cidadão está no local e ainda não está a orientar outro caso."""
        accepted = self.at_scene() and self.guidance is None
        await self.reply(inc, GuidanceAck(act.candidate_id, accepted), performative="agree" if accepted else "refuse")
        if not accepted:
            return
        self.guidance = Guidance(self, act, inc.sender, inc.thread)
        self.open_conversation(self.guidance)
        self.spawn(self.guidance.helper.run, "on_scene_helper")
        self.log("guidance_started", case=act.candidate_id, priority=act.priority)

    async def on_disclosure_request(self, inc: Incoming) -> None:
        """PrivacyGuardian da localização da própria testemunha, que indica onde está o doente (P24)."""
        req: DisclosureRequest = inc.payload
        decision = decide_disclosure(req.field_name, Directory.kind_of(inc.sender), req.priority)
        granted = decision.granted and self.at_scene()
        reason = decision.reason
        if decision.granted and not granted:
            reason = "not_at_scene"
        self.log("disclosure", case=req.case_id, field=req.field_name, to=inc.sender, granted=granted, reason=reason)
        if not granted:
            await self.reply(inc, DisclosureRefusal(req.case_id, req.field_name, reason))
            return
        if req.case_id not in self.active_cases:
            self.spawn(lambda: self.purge_later(req.case_id), "purge_fallback")
        self.active_cases[req.case_id] = req.priority
        await self.reply(inc, Disclosure(req.case_id, req.field_name, [round(c, 1) for c in self.scene]))

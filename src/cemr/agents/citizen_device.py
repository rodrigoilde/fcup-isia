"""CitizenDeviceAgent: um dispositivo vestível ou telemóvel. Papéis SensorMonitor (R1) e PrivacyGuardian (R12).

Os sinais em bruto (sensorStream) nunca saem do dispositivo; só saem resumos. Liveness (análise R1):

    Watch        = _ReadSignals+ . _DetectEvent . (ConfirmFirst | AlertFirst)
    ConfirmFirst = _PromptWearer . [RaiseCandidateAlert]
    AlertFirst   = RaiseCandidateAlert . _PromptWearer . [CancelAlert]

A política "adaptive" usa AlertFirst só quando os sinais sugerem P1, como a análise propõe.
Desenho em docs/03-detailed-design.md §3.
"""

import asyncio
import itertools

from spade.behaviour import CyclicBehaviour

from ..behaviours.privacy import coarse_area, decide_disclosure
from ..protocol.messages_detection import (AlertAck, AlertCancel, AlertReport, CancelAck, CorroborationQuery,
                                           CorroborationReply)
from ..protocol.messages_hubs import Disclosure, DisclosureRefusal, DisclosureRequest, RegistrationAck
from ..protocol.messages_response import CaseClosure
from ..protocol.ontology import (CancelReason, EventType, PromptStatus, RegistrationRole, SensorPolicy, SourceKind,
                                 Verdict)
from ..sim.directory import Directory
from .base import CEMRAgent
from .conversation import NEVER, Incoming


def detect_event(features: dict, confidence: dict) -> tuple[EventType, float]:
    """_DetectEvent: classifica o resumo dos sinais e dá uma confiança local.

    Args:
        features (dict): Resumo dos sinais {fall, immobile, cardiac, quality}.
        confidence (dict): Confiança base de cada tipo de evento (`sensors.event_confidence`).

    Returns:
        tuple[EventType, float]: O tipo de evento e a confiança (a base vezes a qualidade do sinal).
    """
    cardiac_flag = features["cardiac"] in ("absent", "anomalous")
    if features["fall"] and features["immobile"] and cardiac_flag:
        event = EventType.COLLAPSE_CARDIAC
    elif features["fall"] and features["immobile"]:
        event = EventType.FALL_IMMOBILE
    else:
        event = EventType.FALL
    return event, round(features["quality"] * confidence[str(event)], 3)


class Sensing(CyclicBehaviour):
    """_ReadSignals: espera pelo próximo evento de sensor vindo do ambiente."""

    async def run(self) -> None:
        queue = self.agent.world.perceptions(self.agent.label)
        try:
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return
        if event["type"] == "sensor_event":
            self.agent.spawn(lambda: self.agent.alert_episode(event), "alert_episode")


class CitizenDeviceAgent(CEMRAgent):
    """Dispositivo do cidadão: agente de reflexo com modelo (Russell e Norvig, 2022).

    Guarda os alertas recentes (`recent_alerts`) para responder a pedidos de corroboração e decide
    com regras fixas de deteção e de política de alerta.

    Attributes:
        recent_alerts (list[tuple]): (alerta, célula, instante, confiança, área) dos alertas enviados.
    """

    KIND = "device"

    def __init__(self, idx: int, ctx, pos):
        super().__init__(Directory.device(idx), ctx, pos)

    async def on_setup(self) -> None:
        self.alert_ids = itertools.count(1)
        self.recent_alerts: list[tuple] = []
        self.service_handlers = {DisclosureRequest: self.on_disclosure_request}
        self.add_behaviour(Sensing(), NEVER)
        await self.register_with_hubs(RegistrationRole.SENSOR)

    def policy_for(self, event: EventType) -> str:
        """Política de alerta para um tipo de evento (a adaptativa só alerta primeiro em P1)."""
        policy = self.cfg["sensors"]["policy"]
        if policy != SensorPolicy.ADAPTIVE:
            return policy
        if event == EventType.COLLAPSE_CARDIAC:
            return SensorPolicy.ALERT_FIRST
        return SensorPolicy.CONFIRM_FIRST

    async def alert_episode(self, event: dict) -> None:
        """Um episódio de deteção: alerta e pergunta ao portador, pela ordem da política."""
        etype, confidence = detect_event(event["features"], self.cfg["sensors"]["event_confidence"])
        policy = self.policy_for(etype)
        alert_id = f"{self.label}-a{next(self.alert_ids)}"
        cell = self.cell()
        area = coarse_area(self.pos(), self.cfg["city"]["grid_spacing_m"])
        countdown = self.cfg["wearer"]["prompt_countdown_s"]
        response = self.world.wearer_response(self.label)            # wearerResponse[d]
        answered = response is not None and response <= countdown
        prompt_s = response if answered else countdown
        self.recent_alerts.append((alert_id, cell, self.now(), confidence, area))
        self.log("sensor_event", alert=alert_id, event_type=str(etype), confidence=confidence, policy=str(policy))

        def report(prompt: str) -> AlertReport:
            return AlertReport(alert_id, SourceKind.SENSOR, str(etype), confidence, cell, area, event["t"],
                               str(policy), str(prompt))

        if policy == SensorPolicy.ALERT_FIRST:
            await self.alert_first(alert_id, cell, report, prompt_s, answered)
            return
        await self.sleep(prompt_s)                                     # _PromptWearer
        if answered:
            self.log("alert_suppressed", alert=alert_id)
        else:
            await self.raise_alert(report(PromptStatus.NO_RESPONSE), cell)

    async def alert_first(self, alert_id: str, cell: int, report, prompt_s: float, answered: bool) -> None:
        """AlertFirst: alerta já, pergunta ao portador e depois cancela ou confirma o silêncio."""
        prompt_end = self.now() + prompt_s
        await self.raise_alert(report(PromptStatus.PENDING), cell)    # espera pelo AlertAck (F6)
        await self.sleep(prompt_end - self.now())                     # _PromptWearer
        if answered:
            await self.follow_up(AlertCancel(alert_id, CancelReason.WEARER_OK, self.now()), cell, alert_id)
            self.log("wearer_answered", alert=alert_id)
        else:
            await self.follow_up(report(PromptStatus.NO_RESPONSE), cell, alert_id)

    async def on_message(self, inc: Incoming) -> None:
        p = inc.payload
        if isinstance(p, CorroborationQuery):
            await self.corroborate(inc, p)
        elif isinstance(p, CaseClosure):
            self.purge(p.case_id)                                       # _PurgeCaseData (OS11)
        elif isinstance(p, (AlertAck, CancelAck, RegistrationAck)):
            pass
        else:
            await super().on_message(inc)

    async def corroborate(self, inc: Incoming, query: CorroborationQuery) -> None:
        """_SummariseEvidence (P03): só sai do dispositivo um veredicto, uma confiança e a área do alerta."""
        matches = [a for a in self.recent_alerts
                   if a[1] == query.cell and query.window_from <= a[2] <= query.window_to]
        if matches:
            last = matches[-1]
            await self.reply(inc, CorroborationReply(query.candidate_id, Verdict.CONFIRM, last[3], last[4]))
        else:
            await self.reply(inc, CorroborationReply(query.candidate_id, Verdict.NO_DATA, 0.0))

    async def on_disclosure_request(self, inc: Incoming) -> None:
        """PrivacyGuardian (R12) do portador: P24 com necessidade de saber e interesses vitais (D7)."""
        req: DisclosureRequest = inc.payload
        decision = decide_disclosure(req.field_name, Directory.kind_of(inc.sender), req.priority)
        self.log("disclosure", case=req.case_id, field=req.field_name, to=inc.sender, granted=decision.granted,
                 reason=decision.reason)
        if not decision.granted:
            await self.reply(inc, DisclosureRefusal(req.case_id, req.field_name, decision.reason))
            return
        if req.case_id not in self.active_cases:
            self.spawn(lambda: self.purge_later(req.case_id), "purge_fallback")
        self.active_cases[req.case_id] = req.priority
        position = [round(c, 1) for c in self.pos()]
        await self.reply(inc, Disclosure(req.case_id, req.field_name, position))

"""CitizenDeviceAgent: a wearable or phone. SensorMonitor (R1) + PrivacyGuardian (R12) of its wearer.

Raw signals (sensorStream) never leave the device; only summaries do. Liveness (analysis R1):
    Watch        = _ReadSignals+ . _DetectEvent . (ConfirmFirst | AlertFirst)
    ConfirmFirst = _PromptWearer . [RaiseCandidateAlert]
    AlertFirst   = RaiseCandidateAlert . _PromptWearer . [CancelAlert]
The "adaptive" policy uses AlertFirst only when the signals suggest P1, as the analysis proposes.
"""

import asyncio
import itertools

from spade.behaviour import CyclicBehaviour

from ..behaviours.privacy import decide_disclosure
from ..protocol.messages import (AlertAck, AlertCancel, AlertReport, CancelAck, CaseClosure, CorroborationQuery,
                                 CorroborationReply, Disclosure, DisclosureRefusal, DisclosureRequest,
                                 RegistrationAck)
from ..protocol.ontology import (CancelReason, EventType, PromptStatus, RegistrationRole, SensorPolicy,
                                 SourceKind, Verdict)
from ..sim.directory import Directory
from .base import CEMRAgent, Incoming

EVENT_CONFIDENCE = {EventType.COLLAPSE_CARDIAC: 0.95, EventType.FALL_IMMOBILE: 0.8, EventType.FALL: 0.5}


def detect_event(features: dict) -> tuple[EventType, float]:
    """_DetectEvent: classify the summarised signals and give a local confidence."""
    cardiac_flag = features["cardiac"] in ("absent", "anomalous")
    if features["fall"] and features["immobile"] and cardiac_flag:
        event = EventType.COLLAPSE_CARDIAC
    elif features["fall"] and features["immobile"]:
        event = EventType.FALL_IMMOBILE
    else:
        event = EventType.FALL
    return event, round(features["quality"] * EVENT_CONFIDENCE[event], 3)


class Sensing(CyclicBehaviour):
    """_ReadSignals: wait for the next sensor event from the environment."""

    async def run(self):
        queue = self.agent.world.perceptions(self.agent.label)
        try:
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return
        if event["type"] == "sensor_event":
            self.agent.spawn(lambda: self.agent.alert_episode(event), "alert_episode")


class CitizenDeviceAgent(CEMRAgent):
    KIND = "device"

    def __init__(self, idx: int, ctx, pos):
        super().__init__(Directory.device(idx), ctx, pos)

    async def on_setup(self):
        self._alert_ids = itertools.count(1)
        self.recent_alerts: list[tuple[str, int, float, float]] = []    # (alert id, cell, t, confidence)
        self.active_cases: dict[str, str] = {}                          # case -> priority (for P24)
        self.service_handlers = {DisclosureRequest: self.on_disclosure_request}
        self.add_worker_behaviour(Sensing())
        await self.register_with_hubs(RegistrationRole.SENSOR)

    def policy_for(self, event: EventType) -> str:
        policy = self.cfg["sensors"]["policy"]
        if policy == SensorPolicy.ADAPTIVE:
            return SensorPolicy.ALERT_FIRST if event == EventType.COLLAPSE_CARDIAC else SensorPolicy.CONFIRM_FIRST
        return policy

    async def alert_episode(self, event: dict) -> None:
        etype, confidence = detect_event(event["features"])
        policy = self.policy_for(etype)
        alert_id = f"{self.label}-a{next(self._alert_ids)}"
        cell = self.cell()
        countdown = self.cfg["wearer"]["prompt_countdown_s"]
        response = self.world.wearer_response(self.label)               # wearerResponse[d]
        answered = response is not None and response <= countdown
        self.recent_alerts.append((alert_id, cell, self.now(), confidence))
        self.log("sensor_event", alert=alert_id, event_type=str(etype), confidence=confidence, policy=str(policy))

        def report(prompt):
            return AlertReport(alert_id, SourceKind.SENSOR, str(etype), confidence, cell, event["t"], str(policy),
                               str(prompt), event["features"]["quality"])

        if policy == SensorPolicy.ALERT_FIRST:
            prompt_end = self.now() + (response if answered else countdown)
            await self.raise_alert(report(PromptStatus.PENDING), cell)    # waits for the AlertAck (F6)
            await self.sleep(prompt_end - self.now())                     # _PromptWearer
            if answered:
                await self.follow_up(AlertCancel(alert_id, CancelReason.WEARER_OK, self.now()), cell, alert_id)
                self.log("wearer_answered", alert=alert_id)
            else:
                await self.follow_up(report(PromptStatus.NO_RESPONSE), cell, alert_id)
        else:
            await self.sleep(response if answered else countdown)
            if answered:
                self.log("alert_suppressed", alert=alert_id)
            else:
                await self.raise_alert(report(PromptStatus.NO_RESPONSE), cell)

    async def on_message(self, inc: Incoming) -> None:
        p = inc.payload
        if isinstance(p, CorroborationQuery):
            # _SummariseEvidence: only a verdict and a confidence leave the device.
            match = [a for a in self.recent_alerts if a[1] == p.cell and p.window_from <= a[2] <= p.window_to]
            if match:
                await self.reply(inc, CorroborationReply(p.candidate_id, Verdict.CONFIRM, match[-1][3]))
            else:
                await self.reply(inc, CorroborationReply(p.candidate_id, Verdict.NO_DATA, 0.0))
        elif isinstance(p, CaseClosure):
            if self.active_cases.pop(p.case_id, None) is not None:
                self.log("purge", case=p.case_id)                       # _PurgeCaseData (OS11)
        elif isinstance(p, (AlertAck, CancelAck, RegistrationAck)):
            pass
        else:
            await super().on_message(inc)

    async def on_disclosure_request(self, inc: Incoming) -> None:
        """PrivacyGuardian (R12) of the wearer: P24 with need-to-know and vital interests (D7)."""
        req: DisclosureRequest = inc.payload
        decision = decide_disclosure(req.field_name, Directory.kind_of(inc.sender), req.priority)
        self.log("disclosure", case=req.case_id, field=req.field_name, to=inc.sender, granted=decision.granted,
                 reason=decision.reason)
        if decision.granted:
            if req.case_id not in self.active_cases:
                self.spawn(lambda case=req.case_id: self.purge_later(case), "purge_fallback")
            self.active_cases[req.case_id] = req.priority
            await self.reply(inc, Disclosure(req.case_id, req.field_name, [round(c, 1) for c in self.pos()]))
        else:
            await self.reply(inc, DisclosureRefusal(req.case_id, req.field_name, decision.reason))

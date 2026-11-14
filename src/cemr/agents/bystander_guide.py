"""BystanderGuide (R9) e OnSceneHelper (R10): a app de orientação e o leigo que a segue, no telemóvel
de uma testemunha.

O P16 GiveInstruction e o P17 ReportFeedback trocam-se dentro do telemóvel e nunca passam pela rede,
por isso a orientação continua sem cobertura (F13). Ficam registados como mensagens locais.

    Coach = _SelectNextStep . GiveInstruction . (ReportFeedback | _DetectSilence . StatusUpdate)

Desenho em docs/03-detailed-design.md §2.6.
"""

import asyncio
from typing import TYPE_CHECKING

from spade.message import Message

from ..behaviours import guidance as gp
from ..protocol.messages import encode
from ..protocol.messages_assistance import (ActionSummary, Feedback, HandoverRequest, HandoverSummary, HelpEnRoute,
                                            Instruction, TakeoverRequest)
from ..protocol.messages_detection import GuidanceActivation
from ..protocol.messages_hubs import Takeover
from ..protocol.messages_response import CaseClosure, StatusReport
from ..protocol.ontology import ResponderStatus
from .conversation import Conversation, Incoming, Step

if TYPE_CHECKING:
    from .bystander import BystanderAgent


class Helper:
    """OnSceneHelper (R10): o leigo que segue a app. Modelo de comportamento (A5): pode desistir e cansa-se.

    Attributes:
        instructions (asyncio.Queue): Instruções P16 vindas da app (None termina).
        gave_up (bool): Se o ajudante desistiu; a partir daí fica em silêncio.
        cycles (int): Ciclos de compressões feitos.
        cpr_started_at (float | None): Quando começou as compressões.
    """

    def __init__(self, agent: "BystanderAgent", guidance: "Guidance"):
        self.agent = agent
        self.guidance = guidance
        self.instructions: asyncio.Queue = asyncio.Queue()
        self.gave_up = False
        self.cycles = 0
        self.cpr_started_at: float | None = None

    async def run(self) -> None:
        """Segue as instruções até a orientação acabar."""
        a = self.agent
        wcfg = a.cfg["witness"]
        while True:
            instruction = await self.instructions.get()
            if instruction is None:
                return
            if self.gave_up:
                continue                                              # silêncio: a app vai dar por isso
            await a.sleep(a.uniform(wcfg["react_delay_s"]))
            p_give_up = wcfg["p_give_up"] + wcfg["p_give_up_per_cycle"] * max(0, self.cycles - 2)
            if a.rng.random() < p_give_up:
                self.gave_up = True
                a.log("helper_gave_up", case=self.guidance.case_id, step=instruction.step)
                continue
            result = await self.perform(instruction)
            feedback = Feedback(instruction.case_id, result, a.now())
            a.log_local(feedback, "BystanderGuide", self.guidance.thread)            # P17 (local)
            await self.guidance.enqueue(self.guidance.local_message(feedback))

    async def perform(self, instruction: Instruction) -> str:
        """_PerformInstruction e _ObservePatient: faz o passo e diz o que viu."""
        a = self.agent
        seen = a.world.observe_patient(a.scene, a.rng, a.cfg["witness"]["observation_error"])
        if seen is None:
            seen = {"responsive": True, "breathing_normally": True}
        if instruction.step == "CHECK_RESPONSE":
            return gp.WOKE_UP if seen["responsive"] else gp.NO_RESPONSE
        if instruction.step == "CHECK_BREATHING":
            return gp.BREATHING if seen["breathing_normally"] else gp.NOT_BREATHING
        if instruction.step == "COMPRESSIONS":
            if a.world.act_start_cpr(a.scene, a.label) and self.cpr_started_at is None:
                self.cpr_started_at = a.now()
            self.cycles += 1
            await a.sleep(instruction.expected_s)                     # um ciclo de compressões
            return gp.TIRED if self.cycles >= a.cfg["witness"]["tired_after_cycles"] else gp.DONE
        if instruction.step == "KEEP_WATCHING":
            await a.sleep(instruction.expected_s)
            return gp.DONE if seen["breathing_normally"] else gp.NOT_BREATHING
        return gp.DONE


class Guidance(Conversation):
    """BystanderGuide (R9) de um caso: escolhe um passo, dá a instrução e espera pela resposta.

    Attributes:
        case_id (str): Caso orientado.
        coordinator (str): Hub que coordena o caso (muda num takeover P28).
        state (GuideState): O que a app sabe sobre o doente.
        helper (Helper): O ajudante humano.
        silence_reported (bool): Se já avisou o coordenador de que o ajudante se calou (F11).
    """

    def __init__(self, agent: "BystanderAgent", act: GuidanceActivation, coordinator: str, thread: str):
        super().__init__({thread})
        self.witness = agent
        self.case_id = act.candidate_id
        self.coordinator = coordinator
        self.thread = thread
        self.state = gp.GuideState.from_triage(act.triage)
        self.helper = Helper(agent, self)
        self.silence_reported = False
        self.add_state("GUIDE", Guide(self), initial=True)

    def local_message(self, payload) -> Message:
        """Embrulha uma mensagem local (P17) para entrar na fila desta conversa."""
        a = self.witness
        metadata = {"performative": str(payload.PERFORMATIVES[0]), "protocol": payload.PROTOCOL.value}
        return Message(to=str(a.jid), sender=str(a.jid), thread=self.thread, body=encode(payload), metadata=metadata)

    async def finished(self) -> None:
        self.helper.instructions.put_nowait(None)
        self.witness.guidance = None
        self.witness.log("guidance_ended", case=self.case_id)


class Guide(Step):
    """O único estado da orientação: um ciclo de passos até alguém assumir ou o caso fechar."""

    async def step(self) -> None:
        g, a = self.fsm, self.agent
        while True:
            step = gp.next_step(g.state)                                     # _SelectNextStep (OS12)
            instruction = Instruction(g.case_id, step.id, step.text, step.cadence_per_min, step.expected_s)
            a.log_local(instruction, "OnSceneHelper", g.thread)             # P16 (local)
            g.helper.instructions.put_nowait(instruction)
            result = await self.wait_feedback(step, instruction)
            if result is None:
                return
            g.state.apply(step.id, result)

    async def wait_feedback(self, step: gp.Step, instruction: Instruction) -> str | None:
        """Espera pelo P17 do ajudante e trata as outras mensagens do caso entretanto.

        Returns:
            str | None: O resultado reportado, ou None se a orientação acabou (P18, P19 ou fecho).
        """
        g, a = self.fsm, self.agent
        t_silence = a.cfg["witness"]["t_silence_s"]
        deadline = a.now() + step.expected_s + t_silence
        repeated = False
        while True:
            inc = await g.next_incoming(deadline)
            if inc is None:                                                  # _DetectSilence
                if not repeated:
                    repeated = True
                    g.helper.instructions.put_nowait(instruction)            # repete a instrução uma vez
                    deadline = a.now() + step.expected_s + t_silence
                    continue
                await self.report_silence()
                deadline = a.now() + 3600                                    # espera por quem chegue
                continue
            if isinstance(inc.payload, Feedback):
                return inc.payload.result
            if await self.handle(inc):
                return None

    async def report_silence(self) -> None:
        """F11: avisa o coordenador, uma vez, de que o ajudante deixou de responder."""
        g, a = self.fsm, self.agent
        if g.silence_reported:
            return
        g.silence_reported = True
        await a.send_to(g.coordinator, StatusReport(g.case_id, ResponderStatus.WITNESS_SILENT, a.now()),
                        thread=g.thread)

    async def handle(self, inc: Incoming) -> bool:
        """Trata uma mensagem do caso; devolve True se a orientação acaba."""
        g, a = self.fsm, self.agent
        p = inc.payload
        if isinstance(p, HelpEnRoute):                                       # P15: ajuda a caminho
            a.log("help_en_route_received", case=g.case_id, eta_responder=p.eta_responder_s,
                  eta_aed=p.eta_aed_s, eta_ems=p.eta_ems_s)
        elif isinstance(p, Takeover):                                        # P28: novo coordenador
            g.coordinator = p.new_coordinator
        elif isinstance(p, TakeoverRequest):                                 # P18: chegou um voluntário
            await a.reply(inc, ActionSummary(g.case_id, g.helper.cpr_started_at))
            a.log("handed_over", case=g.case_id, to=inc.sender, role=p.arriving_role)
            return True
        elif isinstance(p, HandoverRequest):                                 # P19 sem voluntário no local
            await a.reply(inc, self.handover_summary())
            a.log("handed_over", case=g.case_id, to=inc.sender, role="EMSUnit")
            return True
        elif isinstance(p, CaseClosure):
            a.purge(p.case_id)                                               # OS11
            return True
        return False

    def handover_summary(self) -> HandoverSummary:
        """Resumo para a equipa da ambulância quando não há voluntário no local (P19)."""
        g, a = self.fsm, self.agent
        patient = a.world.patient_at(a.scene)
        shocks = patient.shocks if patient else 0
        first_shock = patient.first_shock_t if patient else None
        state = "guided bystander CPR" if g.helper.cpr_started_at else ""
        return HandoverSummary(g.case_id, a.scene_t, g.helper.cpr_started_at, shocks, first_shock, state)

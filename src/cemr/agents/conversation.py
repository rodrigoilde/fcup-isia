"""Behaviours SPADE comuns a todos os agentes: router, tarefas, atividades periódicas e conversas.

O SPADE entrega uma mensagem a todos os behaviours cujo template coincide, por isso cada agente
tem um único `Router`, sem template, e todos os outros behaviours levam o template `NEVER`.
O router encaminha cada mensagem de forma explícita (ver `CEMRAgent.route`).

Tipos de behaviour e a expressão de liveness Gaia que implementam (docs/03-detailed-design.md §2.2):

    Router        CyclicBehaviour     o ciclo de mensagens (x)^ω do agente
    Worker        OneShotBehaviour    um episódio, por exemplo avaliar uma call for proposals
    SimPeriodic   PeriodicBehaviour   atividade periódica, com o período em segundos simulados
    Conversation  FSMBehaviour        um caso (hub) ou um compromisso (voluntário, ambulância)

O SPADE retira o behaviour do agente quando ele termina, por isso as tarefas e conversas acabadas
não se acumulam.
"""

import asyncio
from dataclasses import dataclass

from spade.behaviour import CyclicBehaviour, FSMBehaviour, OneShotBehaviour, PeriodicBehaviour, State
from spade.message import Message
from spade.template import BaseTemplate


class NeverTemplate(BaseTemplate):
    """Template que não coincide com nenhuma mensagem."""

    def match(self, message) -> bool:
        return False


NEVER = NeverTemplate()


@dataclass
class Incoming:
    """Mensagem recebida, já descodificada.

    Attributes:
        msg (Message): Mensagem SPADE original.
        payload (object): Conteúdo descodificado (uma das dataclasses de `protocol.messages_*`).
        sender (str): Nome (pseudónimo) do remetente.
        thread (str | None): Thread da mensagem, que faz de conversation-id.
        performative (str): Performativa FIPA.
    """

    msg: Message
    payload: object
    sender: str
    thread: str | None
    performative: str


class Router(CyclicBehaviour):
    """Recebe todas as mensagens do agente e passa-as a `CEMRAgent.route`."""

    async def run(self) -> None:
        msg = await self.receive(timeout=1.0)
        if msg is not None:
            await self.agent.route(msg)


class Worker(OneShotBehaviour):
    """Corre uma corrotina uma vez; um erro fica no registo de eventos em vez de parar o agente."""

    def __init__(self, coro_factory, label: str):
        super().__init__()
        self.coro_factory = coro_factory
        self.label = label

    async def run(self) -> None:
        try:
            await self.coro_factory()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - o erro vai para o registo de eventos
            self.agent.report_error(self.label)


class SimPeriodic(PeriodicBehaviour):
    """Atividade periódica (_DecayTrust, ShareReputation, heartbeats) com período em segundos simulados."""

    def __init__(self, agent, sim_period: float, coro_factory, label: str):
        super().__init__(period=agent.real(sim_period))
        self.coro_factory = coro_factory
        self.label = label

    async def run(self) -> None:
        try:
            await self.coro_factory()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - o erro vai para o registo de eventos
            self.agent.report_error(self.label)


class ConversationStopped(Exception):
    """O agente parou (fim do run ou falha): sai-se do estado atual sem fazer mais nada."""


class Conversation(FSMBehaviour):
    """Uma FSM por caso (hub) ou compromisso (voluntário, ambulância), alimentada só pelo router.

    Attributes:
        threads (set[str]): Threads cujas mensagens pertencem a esta conversa.
    """

    def __init__(self, threads):
        super().__init__()
        self.threads = set(threads)

    async def next_incoming(self, deadline: float) -> Incoming | None:
        """Próxima mensagem da conversa, ou None quando o prazo (tempo simulado) passa.

        O `kill()` do SPADE só atua entre iterações e os nossos estados fazem ciclos dentro de uma
        iteração, por isso a paragem é verificada aqui: um hub que falhou não pode continuar a
        agir sobre os seus casos (OS1).

        Raises:
            ConversationStopped: Se o agente ou a conversa foram parados.
        """
        if self.is_killed() or self.agent.stopped:
            raise ConversationStopped()
        remaining = deadline - self.agent.now()
        if remaining <= 0:
            msg = await self.receive(timeout=None)          # não bloqueia: só esvazia o que está na fila
        else:
            msg = await self.receive(timeout=max(1e-4, self.agent.real(remaining)))
        if msg is None:
            return None
        return self.agent.parse(msg)

    async def finished(self) -> None:
        """Chamado uma vez quando a FSM chega a um estado final; as subclasses redefinem-no."""

    async def on_end(self) -> None:
        self.agent.close_conversation(self)
        try:
            await self.finished()
        except Exception:  # noqa: BLE001 - o erro vai para o registo de eventos
            self.agent.report_error(f"{type(self).__name__}.finished")


class Step(State):
    """Um estado de uma Conversation. As subclasses implementam `step()` e chamam `set_next_state`.

    Attributes:
        fsm (Conversation): A conversa a que o estado pertence.
    """

    def __init__(self, fsm: Conversation):
        super().__init__()
        self.fsm = fsm

    async def run(self) -> None:
        self.next_state = None          # o SPADE guarda o valor anterior quando se volta a um estado
        try:
            await self.step()
        except asyncio.CancelledError:
            raise
        except ConversationStopped:
            self.next_state = None
        except Exception:  # noqa: BLE001 - o erro vai para o registo de eventos e a FSM termina
            self.next_state = None
            self.agent.report_error(f"{type(self.fsm).__name__}.{type(self).__name__}")

    async def step(self) -> None:
        """Corpo do estado."""
        raise NotImplementedError

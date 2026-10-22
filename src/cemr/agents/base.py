"""Base class of every CEMR agent: message routing, the send path, conversations and workers.

Routing. SPADE gives a message to every behaviour whose template matches, so each agent has a
single Router (no template) and every other behaviour uses NEVER. The router forwards:
  1. service requests (payload types in `service_handlers`) to their handler, whatever the thread;
  2. messages of an open conversation (by thread) to that conversation's FSM;
  3. everything else to `on_message`.

Behaviour types (liveness -> SPADE, docs/03 §2):
  Router                CyclicBehaviour   the agent's (x)^ω message loop
  Worker                OneShotBehaviour  one episode, e.g. evaluating a call for proposals
  SimPeriodic           PeriodicBehaviour periodic activity with a period in simulated seconds
  Conversation          FSMBehaviour      one case or commitment, states are Step subclasses
SPADE removes a behaviour from the agent when it finishes (Behaviour._start), so finished workers
and conversations do not accumulate.

Every message leaves through `send_to`, which applies the network model (latency, loss, coverage)
and writes the "msg" event used for M8.
"""

import asyncio
import itertools
import sys
import traceback
from dataclasses import dataclass

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, FSMBehaviour, OneShotBehaviour, PeriodicBehaviour, State
from spade.message import Message

from ..protocol.messages import AlertAck, Deregistration, Registration, decode, encode
from ..protocol.ontology import LANGUAGE, ONTOLOGY
from ..protocol.templates import NEVER
from ..sim.context import SimContext
from ..sim.directory import Directory


@dataclass
class Incoming:
    msg: Message
    payload: object
    sender: str
    thread: str | None
    performative: str


class Router(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=1.0)
        if msg is not None:
            await self.agent.route(msg)


class Worker(OneShotBehaviour):
    def __init__(self, coro_factory, label: str):
        super().__init__()
        self._factory = coro_factory
        self.label = label

    async def run(self):
        try:
            await self._factory()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - surfaced in the event log
            self.agent.report_error(self.label)


class SimPeriodic(PeriodicBehaviour):
    """A periodic activity (e.g. _DecayTrust, ShareReputation, heartbeats) with a simulated period."""

    def __init__(self, agent, sim_period: float, coro_factory, label: str):
        super().__init__(period=agent.real(sim_period))
        self._factory = coro_factory
        self.label = label

    async def run(self):
        try:
            await self._factory()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            self.agent.report_error(self.label)


class ConversationStopped(Exception):
    """The agent stopped (end of run or crash): leave the current state without acting further."""


class Conversation(FSMBehaviour):
    """One FSM per case (hub) or commitment (volunteer, EMS). Fed only by the agent's router."""

    def __init__(self, threads):
        super().__init__()
        self.threads = set(threads)

    async def next_incoming(self, deadline: float) -> Incoming | None:
        """Next message for this conversation, or None once `deadline` (sim time) passes.

        SPADE's kill() only takes effect between iterations, and our states loop inside one iteration,
        so the stop is checked here: a crashed hub must not keep acting on its cases (OS1).
        """
        if self.is_killed() or self.agent.stopped:
            raise ConversationStopped()
        remaining = deadline - self.agent.now()
        if remaining <= 0:
            msg = await self.receive(timeout=None)          # non-blocking: drain what is queued
        else:
            msg = await self.receive(timeout=max(1e-4, self.agent.real(remaining)))
        return None if msg is None else self.agent.parse(msg)

    async def finished(self):
        """Hook for subclasses, run once the FSM reaches a final state."""

    async def on_end(self):
        self.agent.close_conversation(self)
        try:
            await self.finished()
        except Exception:  # noqa: BLE001
            self.agent.report_error(f"{type(self).__name__}.finished")


class Step(State):
    """A state of a Conversation. Subclasses implement `step()` and call `set_next_state`."""

    def __init__(self, fsm: Conversation):
        super().__init__()
        self.fsm = fsm

    async def run(self):
        self.next_state = None   # SPADE keeps the previous value when a state is re-entered
        try:
            await self.step()
        except asyncio.CancelledError:
            raise
        except ConversationStopped:
            self.next_state = None
        except Exception:  # noqa: BLE001 - surfaced in the event log; the FSM then ends
            self.next_state = None
            self.agent.report_error(f"{type(self.fsm).__name__}.{type(self).__name__}")

    async def step(self):
        raise NotImplementedError


class CEMRAgent(Agent):
    KIND = "agent"

    def __init__(self, name: str, ctx: SimContext, pos):
        super().__init__(ctx.directory.jid(name), ctx.password)
        self.label = name
        self.ctx = ctx
        self.home = tuple(pos)
        self.rng = ctx.rng_for(name)
        self.conversations: dict[str, Conversation] = {}
        self.service_handlers: dict[type, object] = {}
        self.router: Router | None = None
        self.registered_hubs: dict[int, int] = {}
        self._seq = itertools.count(1)
        self._pending: set[asyncio.Task] = set()
        self._acks: dict[str, asyncio.Event] = {}
        self.stopped = False             # set by stop(); SPADE's is_alive() is also False during setup()
        self.alert_hub: dict[str, str] = {}          # alert id -> hub that acknowledged it

    # --- convenience ------------------------------------------------------------------------
    @property
    def cfg(self) -> dict:
        return self.ctx.cfg

    @property
    def world(self):
        return self.ctx.world

    def now(self) -> float:
        return self.ctx.clock.now()

    def real(self, sim_seconds: float) -> float:
        return self.ctx.clock.to_real(sim_seconds)

    async def sleep(self, sim_seconds: float) -> None:
        await self.ctx.clock.sleep(sim_seconds)

    def pos(self):
        return self.world.position(self.label)

    def cell(self) -> int:
        return self.world.cell_of_agent(self.label)

    def uniform(self, bounds) -> float:
        return self.rng.uniform(*bounds)

    def log(self, kind: str, **fields) -> None:
        self.ctx.log.write(kind, agent=self.label, **fields)

    def report_error(self, where: str) -> None:
        trace = traceback.format_exc()
        self.log("error", where=where, trace=trace)
        print(f"[{self.label}] error in {where}:\n{trace}", file=sys.stderr)

    # --- lifecycle --------------------------------------------------------------------------
    async def setup(self):
        self.world.register(self.label, self.home, self.KIND)
        self.router = Router()
        self.add_behaviour(self.router)          # no template: the only behaviour that sees messages
        await self.on_setup()

    async def on_setup(self):
        """Agent-specific setup; runs after the router exists, so it may send messages."""

    async def stop(self) -> None:
        self.stopped = True
        await super().stop()

    def spawn(self, coro_factory, label: str) -> Worker:
        worker = Worker(coro_factory, label)
        self.add_behaviour(worker, NEVER)
        return worker

    def add_worker_behaviour(self, behaviour) -> None:
        self.add_behaviour(behaviour, NEVER)

    def every(self, sim_period: float, coro_factory, label: str) -> SimPeriodic:
        behaviour = SimPeriodic(self, sim_period, coro_factory, label)
        self.add_behaviour(behaviour, NEVER)
        return behaviour

    def open_conversation(self, conv: Conversation) -> None:
        for thread in conv.threads:
            self.conversations[thread] = conv
        self.add_behaviour(conv, NEVER)

    def claim(self, thread: str, conv: Conversation) -> None:
        conv.threads.add(thread)
        self.conversations[thread] = conv

    def close_conversation(self, conv: Conversation) -> None:
        for thread in list(conv.threads):
            if self.conversations.get(thread) is conv:
                del self.conversations[thread]

    # --- receiving --------------------------------------------------------------------------
    def parse(self, msg: Message) -> Incoming:
        return Incoming(msg, decode(msg.body), self.ctx.directory.name_of(msg.sender), msg.thread,
                        msg.get_metadata("performative"))

    async def route(self, msg: Message) -> None:
        try:
            inc = self.parse(msg)
        except Exception:  # noqa: BLE001
            self.report_error("parse")
            return
        if isinstance(inc.payload, AlertAck) and inc.payload.alert_id in self._acks:
            self.alert_hub.setdefault(inc.payload.alert_id, inc.sender)
            self._acks[inc.payload.alert_id].set()
        handler = self.service_handlers.get(type(inc.payload))
        if handler is not None:
            await handler(inc)
            return
        conv = self.conversations.get(inc.thread)
        if conv is not None and not conv.is_done():
            await conv.enqueue(msg)
            return
        try:
            await self.on_message(inc)
        except Exception:  # noqa: BLE001
            self.report_error(f"on_message({type(inc.payload).__name__})")

    async def on_message(self, inc: Incoming) -> None:
        self.log("unhandled", msg_type=type(inc.payload).__name__, sender=inc.sender, thread=inc.thread)

    # --- sending ----------------------------------------------------------------------------
    async def send_to(self, to: str, payload, *, thread: str | None, performative=None) -> bool:
        if self.stopped:                                           # crash-stop: a stopped agent is silent
            return False
        perf = performative or payload.PERFORMATIVES[0]
        if perf not in payload.PERFORMATIVES:
            raise ValueError(f"{type(payload).__name__} cannot travel as {perf}")
        body = encode(payload)
        msg = Message(to=self.ctx.directory.jid(to), sender=str(self.jid), thread=thread, body=body,
                      metadata={"performative": str(perf), "protocol": payload.PROTOCOL.value,
                                "ontology": ONTOLOGY, "language": LANGUAGE, "seq": str(next(self._seq))})
        delivery = self.ctx.net.decide(self.label, to)
        self.ctx.log.write("msg", src=self.label, dst=to, protocol=payload.PROTOCOL.code, perf=str(perf),
                           msg_type=type(payload).__name__, thread=thread, bytes=len(body),
                           delay=delivery.delay_s, dropped=delivery.reason if delivery.dropped else None)
        if delivery.dropped:
            return False
        if delivery.delay_s <= 0:
            await self.router.send(msg)
        else:
            task = asyncio.create_task(self._deliver_later(msg, delivery.delay_s))
            self._pending.add(task)
            task.add_done_callback(self._pending.discard)
        return True

    async def _deliver_later(self, msg: Message, delay_s: float) -> None:
        await self.sleep(delay_s)
        await self.router.send(msg)

    async def reply(self, inc: Incoming, payload, performative=None) -> bool:
        return await self.send_to(inc.sender, payload, thread=inc.thread, performative=performative)

    def log_local(self, payload, peer_role: str, thread: str | None) -> None:
        """Protocols between two roles of the same agent or device (P06, P07, P16, P17)."""
        self.log("local_msg", protocol=payload.PROTOCOL.code, msg_type=type(payload).__name__,
                 peer=peer_role, thread=thread, body=encode(payload))

    # --- PrivacyGuardian fallback (OS11) ------------------------------------------------------
    async def purge_later(self, case_id: str) -> None:
        """Purge a case's disclosed data even if its CaseClosure never arrives (lost message, F5)."""
        await self.sleep(self.cfg["privacy"]["max_retention_s"])
        cases = getattr(self, "active_cases", {})
        if cases.pop(case_id, None) is not None:
            self.log("purge", case=case_id, fallback=True)

    # --- P01 with acknowledgement and fallback (F6: the cell's hub may be down) -----------------
    def hubs_for_cell(self, cell: int) -> list[str]:
        """The cell's hub, then its successors (neighbours by id), as every hub computes them (D8)."""
        return [Directory.hub(cell)] + [Directory.hub(h) for h in sorted(self.world.grid.neighbours[cell])]

    async def raise_alert(self, report, cell: int) -> str | None:
        """Send P01 to the cell's hub; without an AlertAck in time, try its successor. Returns the hub used."""
        timeout = self.cfg["verification"]["alert_ack_timeout_s"]
        event = self._acks.setdefault(report.alert_id, asyncio.Event())
        for hub in self.hubs_for_cell(cell)[:3]:
            await self.send_to(hub, report, thread=report.alert_id)
            try:
                await asyncio.wait_for(event.wait(), timeout=self.real(timeout))
                return self.alert_hub.get(report.alert_id, hub)
            except asyncio.TimeoutError:
                self.log("alert_unacknowledged", alert=report.alert_id, hub=hub)
        return None

    async def follow_up(self, payload, cell: int, alert_id: str) -> None:
        """Later messages about an alert go to whichever hub acknowledged it."""
        hub = self.alert_hub.get(alert_id, Directory.hub(cell))
        await self.send_to(hub, payload, thread=alert_id)

    # --- P25 RegisterInCell (shared by volunteers, bystanders and devices) ---------------------
    async def register_with_hubs(self, role: str, qualification: str = "NONE") -> None:
        """Register with every hub up to the configured ring of the current cell (D3)."""
        cell = self.cell()
        radius = self.cfg["registration"]["ring"][role]
        wanted = self.world.grid.ring(cell, radius)
        thread = f"reg-{self.label}"
        for hub_id, dist in sorted(wanted.items()):
            if self.registered_hubs.get(hub_id) != dist:
                await self.send_to(Directory.hub(hub_id), Registration(role, qualification, cell, dist),
                                   thread=thread)
        for hub_id in sorted(set(self.registered_hubs) - set(wanted)):
            await self.send_to(Directory.hub(hub_id), Deregistration(role), thread=thread)
        self.registered_hubs = dict(wanted)

"""Classe base de todos os agentes CEMR: encaminhamento, envio, conversas e tarefas.

Encaminhamento (`route`). O router passa:

1. os pedidos de serviço (tipos em `service_handlers`) ao seu handler, seja qual for a thread;
2. as mensagens de uma conversa aberta (pela thread) à FSM dessa conversa;
3. o resto a `on_message`.

Todas as mensagens saem por `send_to`, que aplica o modelo de rede (latência, perda, cobertura) e
escreve o evento "msg" usado na métrica M8. Desenho em docs/03-detailed-design.md §2.1.
"""

import asyncio
import itertools
import traceback

from spade.agent import Agent
from spade.message import Message

from ..protocol.messages import decode, encode
from ..protocol.messages_detection import AlertAck
from ..protocol.messages_hubs import Deregistration, Registration
from ..protocol.ontology import LANGUAGE, ONTOLOGY
from ..sim.context import SimContext
from ..sim.directory import Directory
from .conversation import NEVER, Conversation, Incoming, Router, SimPeriodic, Worker


def envelope(payload, performative: str, seq: int) -> dict:
    """Parâmetros FIPA-ACL da mensagem, na metadata do SPADE (docs/04-protocols-and-messages.md §1).

    Uma mensagem com prazo de resposta (`reply_by`) leva-o também no parâmetro FIPA reply-by.
    """
    metadata = {"performative": str(performative), "protocol": payload.PROTOCOL.value, "ontology": ONTOLOGY,
                "language": LANGUAGE, "seq": str(seq)}
    reply_by = getattr(payload, "reply_by", None)
    if reply_by is not None:
        metadata["reply-by"] = str(round(reply_by, 3))
    return metadata


class CEMRAgent(Agent):
    """Agente SPADE com o relógio simulado, o modelo de rede e o registo de eventos.

    Attributes:
        label (str): Nome (pseudónimo) do agente.
        ctx (SimContext): Contexto da simulação.
        home (tuple): Posição inicial.
        rng (random.Random): Gerador aleatório próprio, derivado da seed.
        conversations (dict[str, Conversation]): Conversa aberta de cada thread.
        service_handlers (dict[type, object]): Handler de cada tipo de pedido de serviço.
        registered_hubs (dict[int, int]): Hubs onde o agente está registado e a distância em anéis.
        active_cases (dict[str, str]): Casos cujos dados o agente divulgou (PrivacyGuardian), com a prioridade.
        stopped (bool): Se o agente parou (fim do run ou falha).
    """

    KIND = "agent"

    def __init__(self, name: str, ctx: SimContext, pos):
        super().__init__(ctx.directory.jid(name), ctx.password, port=ctx.xmpp_port)
        self.label = name
        self.ctx = ctx
        self.home = tuple(pos)
        self.rng = ctx.rng_for(name)
        self.conversations: dict[str, Conversation] = {}
        self.service_handlers: dict[type, object] = {}
        self.router: Router | None = None
        self.registered_hubs: dict[int, int] = {}
        self.active_cases: dict[str, str] = {}
        self.seq = itertools.count(1)
        self.pending: set[asyncio.Task] = set()
        self.acks: dict[str, asyncio.Event] = {}
        self.alert_hub: dict[str, str] = {}         # alerta -> hub que o confirmou
        self.stopped = False                        # o is_alive() do SPADE também é False durante o setup()

    # --- atalhos ------------------------------------------------------------------------------------
    @property
    def cfg(self) -> dict:
        """Configuração do cenário."""
        return self.ctx.cfg

    @property
    def world(self):
        """O ambiente."""
        return self.ctx.world

    def now(self) -> float:
        """Instante simulado atual."""
        return self.ctx.clock.now()

    def real(self, sim_seconds: float) -> float:
        """Converte segundos simulados em segundos reais."""
        return self.ctx.clock.to_real(sim_seconds)

    async def sleep(self, sim_seconds: float) -> None:
        """Espera em tempo simulado."""
        await self.ctx.clock.sleep(sim_seconds)

    def pos(self):
        """Posição atual do agente."""
        return self.world.position(self.label)

    def cell(self) -> int:
        """Célula onde o agente está."""
        return self.world.cell_of_agent(self.label)

    def uniform(self, bounds) -> float:
        """Valor uniforme entre os dois limites de `bounds`."""
        return self.rng.uniform(bounds[0], bounds[1])

    def log(self, kind: str, **fields) -> None:
        """Escreve um evento no registo, em nome deste agente.

        Um agente parado não regista ações: uma corrotina que já tinha passado `next_incoming` ainda
        pode dar alguns passos depois do `stop()`, mas as suas mensagens são suprimidas (`send_to`),
        por isso essas ações nunca aconteceram (OS1). Só os erros continuam a ser registados.
        """
        if self.stopped and kind != "error":
            return
        self.ctx.log.write(kind, agent=self.label, **fields)

    def report_error(self, where: str) -> None:
        """Regista a exceção atual no registo de eventos (conta para `errors` no summary.json)."""
        self.log("error", where=where, trace=traceback.format_exc())

    # --- ciclo de vida -------------------------------------------------------------------------------
    async def setup(self) -> None:
        self.world.register(self.label, self.home, self.KIND)
        self.router = Router()
        self.add_behaviour(self.router)           # sem template: o único behaviour que recebe mensagens
        await self.on_setup()

    async def on_setup(self) -> None:
        """Arranque próprio de cada agente; corre depois de o router existir, por isso pode enviar mensagens."""

    async def stop(self) -> None:
        self.stopped = True
        await super().stop()

    def spawn(self, coro_factory, label: str) -> Worker:
        """Corre `coro_factory()` uma vez, num behaviour próprio."""
        worker = Worker(coro_factory, label)
        self.add_behaviour(worker, NEVER)
        return worker

    def every(self, sim_period: float, coro_factory, label: str) -> SimPeriodic:
        """Corre `coro_factory()` periodicamente, com o período em segundos simulados."""
        behaviour = SimPeriodic(self, sim_period, coro_factory, label)
        self.add_behaviour(behaviour, NEVER)
        return behaviour

    def open_conversation(self, conv: Conversation) -> None:
        """Começa uma conversa e associa-lhe as suas threads."""
        for thread in conv.threads:
            self.conversations[thread] = conv
        self.add_behaviour(conv, NEVER)

    def claim(self, thread: str, conv: Conversation) -> None:
        """Associa mais uma thread a uma conversa aberta (por exemplo um alerta fundido num caso)."""
        conv.threads.add(thread)
        self.conversations[thread] = conv

    def close_conversation(self, conv: Conversation) -> None:
        """Esquece as threads de uma conversa terminada."""
        for thread in list(conv.threads):
            if self.conversations.get(thread) is conv:
                del self.conversations[thread]

    # --- receção ------------------------------------------------------------------------------------
    def parse(self, msg: Message) -> Incoming:
        """Descodifica uma mensagem SPADE."""
        return Incoming(msg, decode(msg.body), Directory.name_of(msg.sender), msg.thread,
                        msg.get_metadata("performative"))

    async def route(self, msg: Message) -> None:
        """Encaminha uma mensagem: pedido de serviço, conversa aberta ou `on_message`."""
        try:
            inc = self.parse(msg)
        except (ValueError, KeyError, TypeError):      # JSON inválido ou tipo de mensagem desconhecido
            self.report_error("parse")
            return
        if isinstance(inc.payload, AlertAck) and inc.payload.alert_id in self.acks:
            self.alert_hub.setdefault(inc.payload.alert_id, inc.sender)
            self.acks[inc.payload.alert_id].set()
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
        except Exception:  # noqa: BLE001 - o erro vai para o registo de eventos
            self.report_error(f"on_message({type(inc.payload).__name__})")

    async def on_message(self, inc: Incoming) -> None:
        """Mensagem fora de uma conversa; por omissão só fica registada."""
        self.log("unhandled", msg_type=type(inc.payload).__name__, sender=inc.sender, thread=inc.thread)

    # --- envio -----------------------------------------------------------------------------------------
    async def send_to(self, to: str, payload, *, thread: str | None, performative=None) -> bool:
        """Envia uma mensagem FIPA-ACL através do modelo de rede.

        Args:
            to (str): Nome do destinatário.
            payload: Mensagem (uma das dataclasses de `protocol.messages_*`).
            thread (str | None): Thread da conversa.
            performative: Performativa; por omissão a primeira permitida para a mensagem.

        Returns:
            bool: False se a mensagem se perdeu ou o agente está parado.

        Raises:
            ValueError: Se a performativa não é uma das permitidas para esta mensagem.
        """
        if self.stopped:                             # falha por paragem: um agente parado não fala
            return False
        perf = performative or payload.PERFORMATIVES[0]
        if perf not in payload.PERFORMATIVES:
            raise ValueError(f"{type(payload).__name__} cannot travel as {perf}")
        body = encode(payload)
        msg = Message(to=Directory.jid(to), sender=str(self.jid), thread=thread, body=body,
                      metadata=envelope(payload, perf, next(self.seq)))
        delivery = self.ctx.net.decide(self.label, to)
        dropped = delivery.reason if delivery.dropped else None
        self.ctx.log.write("msg", src=self.label, dst=to, protocol=payload.PROTOCOL.code, perf=str(perf),
                           msg_type=type(payload).__name__, thread=thread, bytes=len(body),
                           delay=delivery.delay_s, dropped=dropped)
        if delivery.dropped:
            return False
        if delivery.delay_s <= 0:
            await self.router.send(msg)
        else:
            task = asyncio.create_task(self.deliver_later(msg, delivery.delay_s))
            self.pending.add(task)
            task.add_done_callback(self.pending.discard)
        return True

    async def deliver_later(self, msg: Message, delay_s: float) -> None:
        """Entrega uma mensagem depois do atraso da rede."""
        await self.sleep(delay_s)
        await self.router.send(msg)

    async def reply(self, inc: Incoming, payload, performative=None) -> bool:
        """Responde ao remetente na mesma thread."""
        return await self.send_to(inc.sender, payload, thread=inc.thread, performative=performative)

    def log_local(self, payload, peer_role: str, thread: str | None) -> None:
        """Regista um protocolo entre dois papéis do mesmo agente ou telemóvel (P06, P07, P16, P17, P21)."""
        self.log("local_msg", protocol=payload.PROTOCOL.code, msg_type=type(payload).__name__,
                 peer=peer_role, thread=thread, body=encode(payload))

    # --- PrivacyGuardian (OS11) ---------------------------------------------------------------------
    def purge(self, case_id: str, fallback: bool = False) -> None:
        """Apaga os dados divulgados de um caso (_PurgeCaseData)."""
        if self.active_cases.pop(case_id, None) is None:
            return
        if fallback:
            self.log("purge", case=case_id, fallback=True)
        else:
            self.log("purge", case=case_id)

    async def purge_later(self, case_id: str) -> None:
        """Apaga os dados de um caso mesmo que o CaseClosure nunca chegue (mensagem perdida, F5)."""
        await self.sleep(self.cfg["privacy"]["max_retention_s"])
        self.purge(case_id, fallback=True)

    # --- P01 com recibo e alternativa (F6: o hub da célula pode estar em baixo) ----------------------
    def hubs_for_cell(self, cell: int) -> list[str]:
        """O hub da célula e depois os seus sucessores (vizinhos por id), como todos os hubs os calculam (D8)."""
        return [Directory.hub(cell)] + [Directory.hub(h) for h in sorted(self.world.grid.neighbours[cell])]

    async def raise_alert(self, report, cell: int) -> str | None:
        """Envia o P01 ao hub da célula; sem AlertAck a tempo, tenta o sucessor.

        Returns:
            str | None: O hub que confirmou o alerta, ou None se nenhum confirmou.
        """
        vcfg = self.cfg["verification"]
        event = self.acks.setdefault(report.alert_id, asyncio.Event())
        for hub in self.hubs_for_cell(cell)[:vcfg["alert_hubs_tried"]]:
            await self.send_to(hub, report, thread=report.alert_id)
            try:
                await asyncio.wait_for(event.wait(), timeout=self.real(vcfg["alert_ack_timeout_s"]))
                return self.alert_hub.get(report.alert_id, hub)
            except asyncio.TimeoutError:
                self.log("alert_unacknowledged", alert=report.alert_id, hub=hub)
        return None

    async def follow_up(self, payload, cell: int, alert_id: str) -> None:
        """As mensagens seguintes sobre um alerta vão para o hub que o confirmou."""
        hub = self.alert_hub.get(alert_id, Directory.hub(cell))
        await self.send_to(hub, payload, thread=alert_id)

    # --- P25 RegisterInCell (voluntários, testemunhas e dispositivos) --------------------------------
    async def register_with_hubs(self, role: str, qualification: str = "NONE") -> None:
        """Regista-se em todos os hubs até ao anel configurado à volta da célula atual (D3)."""
        cell = self.cell()
        radius = self.cfg["registration"]["ring"][role]
        wanted = self.world.grid.ring(cell, radius)
        thread = f"reg-{self.label}"
        for hub_id, dist in sorted(wanted.items()):
            if self.registered_hubs.get(hub_id) != dist:
                await self.send_to(Directory.hub(hub_id), Registration(role, qualification, cell, dist), thread=thread)
        for hub_id in sorted(set(self.registered_hubs) - set(wanted)):
            await self.send_to(Directory.hub(hub_id), Deregistration(role), thread=thread)
        self.registered_hubs = dict(wanted)

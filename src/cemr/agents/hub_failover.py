"""Replicação e recuperação dos casos de um hub (decisão D8, protocolos P27 e P28).

Cada hub envia heartbeats e réplicas dos seus casos declarados ao seu sucessor: o vizinho de menor
id que responde. Um sucessor que não ouve nada durante a lease (mais uma margem) assume os casos
(P28). Os hubs falham por paragem (injeção de falhas); as partições da infraestrutura fixa estão
fora do âmbito, e é isso que mantém um único dono por caso (OS1) sem um protocolo de consenso.
Desenho em docs/03-detailed-design.md §2.7.
"""

from ..protocol.messages_hubs import CaseSnapshot, Heartbeat, HeartbeatAck
from ..sim.directory import Directory
from .case_fsm import CaseFSM
from .case_record import record_from_snapshot
from .conversation import Incoming


class HubFailover:
    """Lado do dono (heartbeats e réplicas) e lado do sucessor (vigiar e assumir) de um hub.

    Attributes:
        successor_index (int): Qual dos vizinhos, por ordem de id, é o sucessor atual.
        last_ack (float): Último HeartbeatAck recebido do sucessor.
        replicas (dict[str, dict[str, CaseSnapshot]]): Hub antecessor -> caso -> última réplica.
        last_heartbeat (dict[str, float]): Último heartbeat de cada antecessor.
        taken_over (set[str]): Antecessores cujos casos já foram assumidos.
    """

    def __init__(self, hub):
        self.hub = hub
        self.successor_index = 0
        self.last_ack = 0.0
        self.replicas: dict[str, dict[str, CaseSnapshot]] = {}
        self.last_heartbeat: dict[str, float] = {}
        self.taken_over: set[str] = set()

    @property
    def successor(self) -> str:
        """Nome do hub sucessor atual."""
        neighbours = self.hub.neighbours
        return Directory.hub(neighbours[self.successor_index % len(neighbours)])

    def lease_s(self) -> float:
        """Duração da lease L, em segundos simulados."""
        fo = self.hub.cfg["failover"]
        return fo["heartbeat_s"] * fo["lease_heartbeats"]

    # --- lado do dono ------------------------------------------------------------------------------
    async def replicate(self, snapshot: CaseSnapshot) -> None:
        """P27: envia a réplica de um caso ao sucessor."""
        await self.hub.send_to(self.successor, snapshot, thread=snapshot.case_id)

    async def heartbeat(self) -> None:
        """P27: heartbeat periódico; se o sucessor se calou, passa ao vizinho seguinte e volta a replicar."""
        hub = self.hub
        now = hub.now()
        lease = self.lease_s()
        if self.last_ack and now - self.last_ack > lease:
            self.successor_index += 1
            self.last_ack = now
            hub.log("successor_changed", successor=self.successor)
            for fsm in list(hub.open_cases.values()):
                await fsm.replicate()
        if not self.last_ack:
            self.last_ack = now
        declared = sorted(case_id for case_id, fsm in hub.open_cases.items() if fsm.declared)
        await hub.send_to(self.successor, Heartbeat(declared, now + lease), thread=f"hb-{hub.label}")

    async def on_heartbeat_ack(self, inc: Incoming) -> None:
        """P27: o sucessor está vivo."""
        self.last_ack = self.hub.now()

    # --- lado do sucessor -----------------------------------------------------------------------------
    async def on_heartbeat(self, inc: Incoming) -> None:
        """P27: guarda a hora do heartbeat e esquece as réplicas de casos que o dono já fechou."""
        self.last_heartbeat[inc.sender] = self.hub.now()
        owned = set(inc.payload.open_cases)
        replicas = self.replicas.get(inc.sender, {})
        for case_id in [c for c in replicas if c not in owned]:
            del replicas[case_id]
        await self.hub.reply(inc, HeartbeatAck(inc.payload.lease_until))

    async def on_snapshot(self, inc: Incoming) -> None:
        """P27: guarda a réplica mais recente de um caso do antecessor."""
        snap: CaseSnapshot = inc.payload
        self.last_heartbeat.setdefault(inc.sender, self.hub.now())
        cases = self.replicas.setdefault(inc.sender, {})
        if snap.closed:
            cases.pop(snap.case_id, None)
        else:
            cases[snap.case_id] = snap

    async def watch_predecessors(self) -> None:
        """P28: assume os casos de um hub cujos heartbeats pararam durante mais do que a lease e a margem."""
        hub = self.hub
        fo = hub.cfg["failover"]
        limit = fo["heartbeat_s"] * (fo["lease_heartbeats"] + fo["takeover_margin_heartbeats"])
        now = hub.now()
        for owner, last in list(self.last_heartbeat.items()):
            if owner in self.taken_over or now - last <= limit:
                continue
            self.taken_over.add(owner)
            cases = self.replicas.pop(owner, {})
            hub.log("takeover", previous=owner, cases=sorted(cases), silent_for=round(now - last, 1))
            for snap in cases.values():
                record = record_from_snapshot(snap, hub.cfg, hub.trust, owner, now)
                fsm = CaseFSM(hub, record, restored=True)
                hub.open_cases[snap.case_id] = fsm
                hub.open_conversation(fsm)

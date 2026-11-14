"""Modelo de rede (pressuposto A3).

O SPADE entrega as mensagens entre agentes do mesmo processo diretamente ao destinatário, sem
passar por XMPP (spikes/README.md). Por isso a latência, a perda e as células sem cobertura são
injetadas aqui, no único caminho de envio do agente base (`CEMRAgent.send_to`).
"""

import math
import random
from dataclasses import dataclass

from .clock import SimClock


@dataclass(frozen=True)
class Delivery:
    """Decisão da rede sobre uma mensagem.

    Attributes:
        dropped (bool): Se a mensagem se perde.
        delay_s (float): Atraso de entrega, em segundos simulados.
        reason (str | None): Motivo da perda: agent_down, no_coverage ou loss.
    """

    dropped: bool
    delay_s: float
    reason: str | None = None


def is_hub(name: str) -> bool:
    """Os hubs são infraestrutura fixa: entre eles há latência, mas não perdas nem falhas de cobertura."""
    return name.startswith("hub")


class NetworkModel:
    """Latência log-normal, perda, zonas sem cobertura e ordem FIFO por ligação.

    Attributes:
        down (set[str]): Agentes que falharam (injeção de falhas); tudo o que lhes diz respeito perde-se.
    """

    def __init__(self, cfg: dict, rng: random.Random, clock: SimClock, world):
        net = cfg["network"]
        self.rng = rng
        self.clock = clock
        self.world = world
        self.mu = math.log(net["latency_median_s"])
        self.sigma = net["latency_sigma"]
        self.max_delay = net["latency_max_s"]
        self.loss = net["loss"]
        self.outages = net.get("outages", [])
        self.last_delivery: dict[tuple[str, str], float] = {}
        self.down: set[str] = set()

    def in_outage(self, name: str) -> bool:
        """Se o agente está numa célula sem cobertura neste momento."""
        if not self.outages or is_hub(name):
            return False
        now = self.clock.now()
        cell = self.world.cell_of_agent(name)
        for outage in self.outages:
            if outage["cell"] == cell and outage["from_s"] <= now < outage["to_s"]:
                return True
        return False

    def decide(self, src: str, dst: str) -> Delivery:
        """Decide se uma mensagem de `src` para `dst` chega e com que atraso."""
        if src == dst:
            return Delivery(False, 0.0)
        if src in self.down or dst in self.down:
            return Delivery(True, 0.0, "agent_down")
        mobile = not (is_hub(src) and is_hub(dst))
        if mobile and (self.in_outage(src) or self.in_outage(dst)):
            return Delivery(True, 0.0, "no_coverage")
        if mobile and self.loss and self.rng.random() < self.loss:
            return Delivery(True, 0.0, "loss")
        # FIFO por ligação, como numa ligação TCP/XMPP: uma mensagem nunca ultrapassa outra
        # anterior do mesmo remetente para o mesmo destinatário.
        now = self.clock.now()
        deliver_at = now + min(self.max_delay, self.rng.lognormvariate(self.mu, self.sigma))
        deliver_at = max(deliver_at, self.last_delivery.get((src, dst), 0.0) + 1e-3)
        self.last_delivery[(src, dst)] = deliver_at
        return Delivery(False, round(deliver_at - now, 4))

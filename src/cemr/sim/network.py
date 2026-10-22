"""Network model (assumption A3).

SPADE hands messages between agents of the same process directly to the receiver, without XMPP
(spikes/README.md). Latency, loss and cells without coverage are therefore injected here, on the
single send path of the base agent.
"""

import math
import random
from dataclasses import dataclass

from .clock import SimClock


@dataclass(frozen=True)
class Delivery:
    dropped: bool
    delay_s: float
    reason: str | None = None


class NetworkModel:
    def __init__(self, cfg: dict, rng: random.Random, clock: SimClock, world):
        net = cfg["network"]
        self.rng = rng
        self.clock = clock
        self.world = world
        self.mu = math.log(net["latency_median_s"])
        self.sigma = net["latency_sigma"]
        self.max_delay = net["latency_max_s"]
        self.loss = net["loss"]
        self.outages = [(o["cell"], o["from_s"], o["to_s"]) for o in net.get("outages", [])]
        self._last_delivery: dict[tuple[str, str], float] = {}
        self.down: set[str] = set()          # crashed agents (fault injection)

    def in_outage(self, name: str) -> bool:
        if not self.outages or name.startswith("hub"):
            return False
        now = self.clock.now()
        cell = self.world.cell_of_agent(name)
        return any(c == cell and start <= now < end for c, start, end in self.outages)

    def decide(self, src: str, dst: str) -> Delivery:
        if src == dst:
            return Delivery(False, 0.0)
        if src in self.down or dst in self.down:
            return Delivery(True, 0.0, "agent_down")
        # Hub-to-hub links are fixed infrastructure: latency, but no loss and no coverage gaps.
        mobile = not (src.startswith("hub") and dst.startswith("hub"))
        if mobile and (self.in_outage(src) or self.in_outage(dst)):
            return Delivery(True, 0.0, "no_coverage")
        if mobile and self.loss and self.rng.random() < self.loss:
            return Delivery(True, 0.0, "loss")
        # Per-link FIFO, as on a TCP/XMPP connection: a message never overtakes an earlier one
        # from the same sender to the same receiver.
        now = self.clock.now()
        deliver_at = now + min(self.max_delay, self.rng.lognormvariate(self.mu, self.sigma))
        deliver_at = max(deliver_at, self._last_delivery.get((src, dst), 0.0) + 1e-3)
        self._last_delivery[(src, dst)] = deliver_at
        return Delivery(False, round(deliver_at - now, 4))

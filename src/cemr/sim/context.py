"""Everything an agent needs from the simulation, bundled so agents stay decoupled from run.py."""

import asyncio
import random
from dataclasses import dataclass

from ..metrics.eventlog import EventLog
from .clock import SimClock
from .directory import Directory
from .network import NetworkModel
from .world import World


@dataclass
class SimContext:
    cfg: dict
    clock: SimClock
    world: World
    net: NetworkModel
    log: EventLog
    directory: Directory
    seed: int
    password: str = "cemr-sim"

    def rng_for(self, name: str) -> random.Random:
        """Per-agent random stream: same seed and name give the same sequence (string seeds are stable)."""
        return random.Random(f"{self.seed}/{name}")


async def start_with_retry(agent, retries: int) -> Exception | None:
    """pyjabber drops connections during login bursts; Agent.start() is safe to retry (spikes/README.md)."""
    for attempt in range(retries + 1):
        try:
            await agent.start(auto_register=True)
            return None
        except Exception as exc:  # noqa: BLE001 - report whatever the last failure was
            if attempt == retries:
                return exc
            await asyncio.sleep(0.2 * 2 ** attempt)


async def start_agents(agents: list, batch: int, retries: int) -> list[tuple[str, Exception]]:
    """Start agents in batches, in list order (hubs first, so registrations find them running)."""
    failures = []
    for i in range(0, len(agents), batch):
        group = agents[i:i + batch]
        results = await asyncio.gather(*(start_with_retry(a, retries) for a in group))
        failures += [(str(a.jid), r) for a, r in zip(group, results) if r is not None]
    return failures

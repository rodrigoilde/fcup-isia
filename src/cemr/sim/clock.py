"""Simulated clock (resource simClock).

SPADE runs in real time, so the simulation runs `factor` times faster than the wall clock. Every
timeout, period and deadline in the code is expressed in simulated seconds and converted here.
"""

import asyncio
import time


class SimClock:
    def __init__(self, factor: float):
        if factor <= 0:
            raise ValueError("clock factor must be positive")
        self.factor = factor
        self._t0: float | None = None

    def start(self) -> None:
        self._t0 = time.monotonic()

    @property
    def started(self) -> bool:
        return self._t0 is not None

    def now(self) -> float:
        """Simulated seconds since start (0 before start)."""
        if self._t0 is None:
            return 0.0
        return (time.monotonic() - self._t0) * self.factor

    def to_real(self, sim_seconds: float) -> float:
        return max(0.0, sim_seconds) / self.factor

    async def sleep(self, sim_seconds: float) -> None:
        await asyncio.sleep(self.to_real(sim_seconds))

    async def sleep_until(self, sim_time: float) -> None:
        await self.sleep(sim_time - self.now())

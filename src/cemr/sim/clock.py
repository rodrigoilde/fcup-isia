"""Relógio simulado (recurso simClock).

O SPADE corre em tempo real, por isso a simulação corre `factor` vezes mais depressa do que o
relógio de parede. Todos os prazos, períodos e esperas do código estão em segundos simulados e são
convertidos aqui. Desenho em docs/03-detailed-design.md §2.3.
"""

import asyncio
import time


class SimClock:
    """Relógio da simulação, acelerado em relação ao tempo real.

    Attributes:
        factor (float): Segundos simulados por segundo real.
    """

    def __init__(self, factor: float):
        if factor <= 0:
            raise ValueError("clock factor must be positive")
        self.factor = factor
        self.t0: float | None = None

    def start(self) -> None:
        """Põe o relógio a contar a partir de 0."""
        self.t0 = time.monotonic()

    def now(self) -> float:
        """Segundos simulados desde o início (0 antes de `start`)."""
        if self.t0 is None:
            return 0.0
        return (time.monotonic() - self.t0) * self.factor

    def to_real(self, sim_seconds: float) -> float:
        """Converte uma duração simulada em segundos reais."""
        return max(0.0, sim_seconds) / self.factor

    async def sleep(self, sim_seconds: float) -> None:
        """Espera uma duração simulada sem bloquear o event loop."""
        await asyncio.sleep(self.to_real(sim_seconds))

    async def sleep_until(self, sim_time: float) -> None:
        """Espera até um instante simulado."""
        await self.sleep(sim_time - self.now())

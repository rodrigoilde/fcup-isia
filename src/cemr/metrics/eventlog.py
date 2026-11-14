"""Registo de eventos só de acrescento, um objeto JSON por linha.

Faz o papel do recurso auditLog (OS10: todas as decisões e divulgações ficam registadas) e é a única
fonte das métricas M1-M13, do verificador de regras e do dashboard. Os registos de verdade de
referência (tipo "gt_*") são escritos pelo ambiente e nunca são lidos pelos agentes.
"""

import json
from pathlib import Path
from typing import Callable

from ..sim.clock import SimClock


class EventLog:
    """Registo de eventos de um run.

    Attributes:
        records (list[dict]): Todos os eventos escritos, pela ordem em que aconteceram.
    """

    def __init__(self, clock: SimClock, path: Path | None = None):
        self.clock = clock
        self.records: list[dict] = []
        self.subscribers: list[Callable[[dict], None]] = []
        self.file = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.file = path.open("w", buffering=1, encoding="utf-8")

    def write(self, kind: str, **fields) -> dict:
        """Escreve um evento com o instante simulado atual e avisa os subscritores (o dashboard)."""
        record = {"t": round(self.clock.now(), 3), "kind": kind, **fields}
        self.records.append(record)
        if self.file is not None:
            self.file.write(json.dumps(record, separators=(",", ":")) + "\n")
        for callback in self.subscribers:
            callback(record)
        return record

    def subscribe(self, callback: Callable[[dict], None]) -> None:
        """Pede para `callback` ser chamado com cada evento novo."""
        self.subscribers.append(callback)

    def close(self) -> None:
        """Fecha o ficheiro do registo."""
        if self.file is not None:
            self.file.close()
            self.file = None


def read_events(path: Path) -> list[dict]:
    """Lê um ficheiro events.jsonl."""
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]

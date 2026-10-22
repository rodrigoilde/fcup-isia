"""Append-only event log, one JSON object per line.

It plays the role of the auditLog resource (OS10: every decision and disclosure is recorded) and is the
single source for the metrics M1–M13, the rule checker and the dashboard. Ground-truth records
(kind "gt_*") are written by the environment and never read by agents.
"""

import json
from pathlib import Path
from typing import Callable

from ..sim.clock import SimClock


class EventLog:
    def __init__(self, clock: SimClock, path: Path | None = None):
        self.clock = clock
        self.records: list[dict] = []
        self._subscribers: list[Callable[[dict], None]] = []
        self._fh = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = path.open("w", buffering=1)

    def write(self, kind: str, **fields) -> dict:
        record = {"t": round(self.clock.now(), 3), "kind": kind, **fields}
        self.records.append(record)
        if self._fh is not None:
            self._fh.write(json.dumps(record, separators=(",", ":")) + "\n")
        for callback in self._subscribers:
            callback(record)
        return record

    def subscribe(self, callback: Callable[[dict], None]) -> None:
        self._subscribers.append(callback)

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None


def read_events(path: Path) -> list[dict]:
    with Path(path).open() as fh:
        return [json.loads(line) for line in fh if line.strip()]

from __future__ import annotations

import heapq
import random
from typing import Any, Callable

from engine.events import Event
from telemetry.sinks import Sink
from telemetry.log_event import LogEvent


class Simulator:
    def __init__(self, seed: int, sink: Sink) -> None:
        random.seed(seed)
        self.seed = seed
        self.t: float = 0.0
        self._q: list[Event] = []
        self._seq = 0
        self.sink = sink

    def schedule(self, t: float, kind: str, handler: Callable[["Simulator", Any], None], data: Any = None) -> None:
        self._seq += 1
        heapq.heappush(self._q, Event(t=t, seq=self._seq, kind=kind, handler=handler, data=data))

    def emit(self, e: LogEvent) -> None:
        self.sink.write(e)

    def run(self, t_end: float, max_events: int = 2_000_000) -> None:
        n = 0
        while self._q and self.t <= t_end and n < max_events:
            ev = heapq.heappop(self._q)
            self.t = ev.t
            ev.handler(self, ev.data)
            n += 1

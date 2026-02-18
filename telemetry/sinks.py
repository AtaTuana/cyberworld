from __future__ import annotations

from typing import List, Protocol
from telemetry.log_event import LogEvent
from telemetry.serializers import to_json_line


class Sink(Protocol):
    def write(self, e: LogEvent) -> None: ...
    def close(self) -> None: ...


class JsonlFileSink:
    def __init__(self, path: str) -> None:
        self.path = path
        self.f = open(path, "a", encoding="utf-8")

    def write(self, e: LogEvent) -> None:
        self.f.write(to_json_line(e) + "\n")

    def close(self) -> None:
        try:
            self.f.flush()
        finally:
            self.f.close()


class MultiSink:
    def __init__(self, sinks: List[Sink]) -> None:
        self.sinks = sinks

    def write(self, e: LogEvent) -> None:
        for s in self.sinks:
            s.write(e)

    def close(self) -> None:
        for s in self.sinks:
            s.close()

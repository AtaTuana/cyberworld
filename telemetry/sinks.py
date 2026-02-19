from __future__ import annotations

import json
from typing import List, Protocol, Any


class Sink(Protocol):
    def write(self, event: Any) -> None: ...
    def close(self) -> None: ...


class JsonlFileSink:
    def __init__(self, path: str) -> None:
        self.path = path
        self.f = open(path, "w", encoding="utf-8")

    def write(self, event: Any) -> None:
        obj = event.to_dict() if hasattr(event, "to_dict") else getattr(event, "__dict__", {})
        self.f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def close(self) -> None:
        try:
            self.f.close()
        except Exception:
            pass


class MultiSink:
    def __init__(self, sinks: List[Sink]) -> None:
        self.sinks = sinks

    def write(self, event: Any) -> None:
        for s in self.sinks:
            s.write(event)

    def close(self) -> None:
        for s in self.sinks:
            s.close()

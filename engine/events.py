from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(order=True)
class Event:
    t: float
    seq: int
    kind: str = field(compare=False)
    handler: Callable[["Simulator", Any], None] = field(compare=False)
    data: Any = field(compare=False, default=None)

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class Process:
    pid: int
    name: str
    owner: str
    cpu_budget: float = 1.0
    state: str = "RUNNABLE"


class ProcessManager:
    def __init__(self) -> None:
        self._pid = 1000
        self.procs: Dict[int, Process] = {}

    def spawn(self, name: str, owner: str, cpu_budget: float = 1.0) -> Process:
        self._pid += 1
        p = Process(pid=self._pid, name=name, owner=owner, cpu_budget=cpu_budget)
        self.procs[p.pid] = p
        return p

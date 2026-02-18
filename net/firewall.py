from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Rule:
    proto: str       # TCP/UDP/*
    dst_port: int    # -1 any
    action: str      # allow/deny


@dataclass
class Firewall:
    rules: List[Rule] = field(default_factory=list)

    def allows(self, proto: str, dst_port: int) -> bool:
        for r in self.rules:
            if r.proto != "*" and r.proto != proto:
                continue
            if r.dst_port != -1 and r.dst_port != dst_port:
                continue
            return r.action == "allow"
        return False

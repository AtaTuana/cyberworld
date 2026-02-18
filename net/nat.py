from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple
import random


@dataclass
class NatMapping:
    inside_ip: str
    inside_port: int
    public_ip: str
    public_port: int


@dataclass
class NatTable:
    public_ip: str
    port_range: Tuple[int, int] = (40000, 65000)
    by_inside: Dict[Tuple[str, int], NatMapping] = field(default_factory=dict)

    def snat(self, inside_ip: str, inside_port: int) -> NatMapping:
        key = (inside_ip, inside_port)
        if key in self.by_inside:
            return self.by_inside[key]
        pub_port = random.randint(*self.port_range)
        m = NatMapping(inside_ip, inside_port, self.public_ip, pub_port)
        self.by_inside[key] = m
        return m

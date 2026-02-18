from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from world.registry import Registry


@dataclass
class NetworkSpec:
    network_id: str
    kind: str              # home/smb/enterprise/campus/cloud/iot
    size: int              # host count
    bandwidth_bps: int     # bytes/sec (sim)
    latency_ms: int
    loss: float


@dataclass
class World:
    world_id: str
    networks: List[NetworkSpec]
    registry: Registry
    meta: Dict[str, str] = field(default_factory=dict)

    def network_by_id(self, nid: str) -> NetworkSpec:
        for n in self.networks:
            if n.network_id == nid:
                return n
        raise KeyError(nid)

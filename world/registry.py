from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from host.host import Host
from net.topology import Topology


@dataclass
class Registry:
    hosts: Dict[str, Host] = field(default_factory=dict)   # host_id -> Host
    topology: Optional[Topology] = None

    def add_host(self, h: Host) -> None:
        self.hosts[h.host_id] = h

    def get_host(self, host_id: str) -> Host:
        return self.hosts[host_id]

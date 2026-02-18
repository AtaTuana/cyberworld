from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RoutingTable:
    # destination network_id -> next hop router id
    routes: Dict[str, str] = field(default_factory=dict)

    def get_next_hop(self, dst_network_id: str) -> Optional[str]:
        return self.routes.get(dst_network_id) or self.routes.get("*")

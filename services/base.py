from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Service:
    name: str
    proto: str
    port: int

    def handle(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        ctx: {
          sim, world, src_host, dst_host, payload, session_id
        }
        """
        raise NotImplementedError

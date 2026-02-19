from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class LogEvent:
    t: float
    device: str
    event_type: str

    src_ip: str
    dst_ip: str
    proto: str
    src_port: int
    dst_port: int

    result: str = "info"
    reason: str = "-"
    bytes: int = 0
    msg: str = "-"
    session_id: str = "-"

    world_id: str = "-"
    network_id: str = "-"
    host_id: str = "-"

    # ✅ identity meta
    actor: str = "-"
    hostname: str = "-"
    username: str = "-"
    identity_type: str = "-"

    extra: Optional[Dict[str, Any]] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("extra") is None:
            d.pop("extra", None)
        return d

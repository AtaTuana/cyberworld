from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict


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

    result: str
    reason: Optional[str] = None

    bytes: int = 0
    msg: Optional[str] = None

    session_id: Optional[str] = None
    world_id: Optional[str] = None
    network_id: Optional[str] = None
    host_id: Optional[str] = None

    extra: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        return asdict(self)

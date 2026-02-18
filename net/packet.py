from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Packet:
    src_ip: str
    dst_ip: str
    proto: str
    src_port: int
    dst_port: int
    size: int
    payload: Any
    session_id: Optional[str] = None

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from net.packet import Packet


@dataclass
class SocketAddr:
    ip: str
    port: int


@dataclass
class VirtualSocket:
    src: SocketAddr
    dst: SocketAddr
    proto: str
    session_id: Optional[str] = None

    def make_packet(self, payload: Any, size: int) -> Packet:
        return Packet(
            src_ip=self.src.ip,
            dst_ip=self.dst.ip,
            proto=self.proto,
            src_port=self.src.port,
            dst_port=self.dst.port,
            size=size,
            payload=payload,
            session_id=self.session_id,
        )

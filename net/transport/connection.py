from __future__ import annotations
from dataclasses import dataclass

from net.transport.socket import VirtualSocket


@dataclass
class Connection:
    sock: VirtualSocket
    state: str = "OPEN"

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    ip: str
    network_id: str
    host_id: str

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Behavior:
    dns_rate: float
    http_rate: float
    auth_rate: float
    file_rate: float

    # anomalies are just parameter changes (no explicit "attack" label)
    auth_error_rate: float = 0.02
    scan_rate: float = 0.0
    exfil_chance: float = 0.0

from __future__ import annotations
from dataclasses import dataclass
import random


@dataclass
class Link:
    bandwidth_bytes_per_sec: int
    latency_ms: int
    loss: float
    jitter_ms: int = 6

    def delay_sec(self, bytes_: int) -> float:
        # serialization time + base latency + jitter
        ser = bytes_ / max(1, self.bandwidth_bytes_per_sec)
        jitter = random.uniform(0, self.jitter_ms) / 1000.0
        return ser + (self.latency_ms / 1000.0) + jitter

    def should_drop(self) -> bool:
        return random.random() < self.loss

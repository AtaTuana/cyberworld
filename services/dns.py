from __future__ import annotations

from typing import Any, Dict
from services.base import Service
from core.constants import PROTO_UDP


class DnsService(Service):
    def __init__(self) -> None:
        super().__init__(name="DNS", proto=PROTO_UDP, port=53)

    def handle(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        payload = ctx.get("payload") or {}
        q = payload.get("q", "unknown")
        return {"ok": True, "answer": f"A 203.0.113.{len(q) % 250 + 1}"}

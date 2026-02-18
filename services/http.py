from __future__ import annotations

from typing import Any, Dict
from services.base import Service
from core.constants import PROTO_TCP


class HttpService(Service):
    def __init__(self) -> None:
        super().__init__(name="HTTP", proto=PROTO_TCP, port=443)

    def handle(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        payload = ctx.get("payload") or {}
        path = payload.get("path", "/")
        return {"ok": True, "status": 200, "path": path}

from __future__ import annotations

from typing import Any, Dict
from services.base import Service
from core.constants import PROTO_TCP


class FileService(Service):
    """
    Virtual file upload/download.
    Stores metadata only on dst VirtualDisk (no large content).
    """
    def __init__(self) -> None:
        super().__init__(name="FILE", proto=PROTO_TCP, port=445)

    def handle(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        dst = ctx["dst_host"]
        payload = ctx.get("payload") or {}
        action = payload.get("action")

        if action == "PUT_META":
            path = payload.get("path", "/uploads/blob.bin")
            size = int(payload.get("size", 0))
            ok = dst.disk.put_file_meta(path=path, size=size, kind="upload", hash_=payload.get("hash", ""))
            if not ok:
                return {"ok": False, "reason": "disk_full"}
            return {"ok": True, "reason": "stored"}

        return {"ok": True, "reason": "noop"}

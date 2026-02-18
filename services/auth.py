from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from services.base import Service
from core.constants import PROTO_TCP


@dataclass
class LockoutState:
    fails: List[float] = field(default_factory=list)
    locked_until: float = 0.0


class AuthService(Service):
    """
    RDP-like auth service:
    - Tracks failures in a window
    - Locks out user after threshold
    """
    def __init__(self, lockout_threshold: int = 25, window_sec: int = 60, lockout_sec: int = 120) -> None:
        super().__init__(name="AUTH", proto=PROTO_TCP, port=3389)
        self.lockout_threshold = lockout_threshold
        self.window_sec = window_sec
        self.lockout_sec = lockout_sec
        self.by_user: Dict[str, LockoutState] = {}

    def handle(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        sim = ctx["sim"]
        dst = ctx["dst_host"]
        payload = ctx.get("payload") or {}
        user = str(payload.get("username", ""))
        pw = str(payload.get("password", ""))

        st = self.by_user.setdefault(user, LockoutState())

        if sim.t < st.locked_until:
            return {"ok": False, "reason": "locked_out"}

        if dst.users.check(user, pw):
            st.fails.clear()
            return {"ok": True, "reason": "login_ok"}

        # fail
        st.fails.append(sim.t)
        cutoff = sim.t - self.window_sec
        while st.fails and st.fails[0] < cutoff:
            st.fails.pop(0)

        if len(st.fails) >= self.lockout_threshold:
            st.locked_until = sim.t + self.lockout_sec
            return {"ok": False, "reason": "locked_out"}

        return {"ok": False, "reason": "bad_password"}

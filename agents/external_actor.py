from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

from engine.sim import Simulator
from telemetry.log_event import LogEvent
from core.ids import next_session_id
from core.rng import chance, rand_int, pick
from core.constants import PROTO_TCP, PROTO_UDP

from net.packet import Packet
from world.world import World
from host.host import Host


def expovariate(rate: float) -> float:
    if rate <= 0:
        return 1e18
    return random.expovariate(rate)


@dataclass
class ExternalProfile:
    kind: str  # customer | partner | remote | attacker
    http_rate: float
    dns_rate: float
    auth_rate: float
    scan_rate: float
    file_rate: float

    auth_error_rate: float = 0.05
    exfil_chance: float = 0.0


class ExternalActorAgent:
    def __init__(self, host: Host, profile: ExternalProfile) -> None:
        self.host = host
        self.p = profile

    def start(self, sim: Simulator, world: World) -> None:
        sim.schedule(sim.t + expovariate(self.p.dns_rate), "TIMER", self._tick_dns, (world,))
        sim.schedule(sim.t + expovariate(self.p.http_rate), "TIMER", self._tick_http, (world,))
        sim.schedule(sim.t + expovariate(self.p.auth_rate), "TIMER", self._tick_auth, (world,))
        sim.schedule(sim.t + expovariate(self.p.file_rate), "TIMER", self._tick_file, (world,))
        if self.p.scan_rate > 0:
            sim.schedule(sim.t + expovariate(self.p.scan_rate), "TIMER", self._tick_scan, (world,))

    def _targets(self, world: World, service_name: str) -> List[Host]:
        return [h for h in world.registry.hosts.values() if h.has_service(service_name)]

    def _pick_target(self, world: World, service_name: str, prefer_network_ids: Optional[List[str]] = None) -> Optional[Host]:
        cands = self._targets(world, service_name)
        if prefer_network_ids:
            preferred = [h for h in cands if h.network_id in prefer_network_ids]
            if preferred:
                return random.choice(preferred)
        return random.choice(cands) if cands else None

    def _deliver(self, sim: Simulator, world: World, dst: Host, pkt: Packet) -> Dict[str, Any]:
        for svc in dst.services.values():
            if svc.proto == pkt.proto and svc.port == pkt.dst_port:
                return svc.handle({
                    "sim": sim,
                    "world": world,
                    "src_host": self.host,
                    "dst_host": dst,
                    "payload": pkt.payload,
                    "session_id": pkt.session_id
                })
        return {"ok": False, "reason": "no_service"}

    def _src_identity(self):
        return (
            getattr(self.host, "display_name", self.host.host_id),
            getattr(self.host, "hostname", "-"),
            getattr(self.host, "username", "-"),
            getattr(self.host, "identity_type", "-"),
        )

    def _dst_identity(self, dst: Host):
        return (
            getattr(dst, "display_name", dst.host_id),
            getattr(dst, "hostname", "-"),
            getattr(dst, "username", "-"),
            getattr(dst, "identity_type", "-"),
        )

    def _send(self, sim: Simulator, world: World, dst: Host, proto: str, dst_port: int,
              payload: Dict[str, Any], size: int, hint: str) -> None:
        topo = world.registry.topology
        assert topo is not None

        session_id = next_session_id("ext_")
        pkt = Packet(
            src_ip=self.host.ip,
            dst_ip=dst.ip,
            proto=proto,
            src_port=rand_int(49152, 65535),
            dst_port=dst_port,
            size=size,
            payload=payload,
            session_id=session_id
        )

        delay, _, outcome = topo.route_packet_delay(pkt, self.host.network_id, dst.network_id)

        src_actor, src_hostname, src_username, src_itype = self._src_identity()

        if outcome != "ok":
            sim.emit(LogEvent(
                t=sim.t,
                device="net",
                event_type="DROP",
                src_ip=pkt.src_ip, dst_ip=pkt.dst_ip,
                proto=pkt.proto, src_port=pkt.src_port, dst_port=pkt.dst_port,
                result="drop",
                reason=outcome,
                bytes=pkt.size,
                msg=hint,
                session_id=session_id,
                world_id=world.world_id,
                network_id=self.host.network_id,
                host_id=self.host.host_id,
                actor=src_actor,
                hostname=src_hostname,
                username=src_username,
                identity_type=src_itype,
            ))
            return

        sim.emit(LogEvent(
            t=sim.t,
            device="net",
            event_type="TX",
            src_ip=pkt.src_ip, dst_ip=pkt.dst_ip,
            proto=pkt.proto, src_port=pkt.src_port, dst_port=pkt.dst_port,
            result="info",
            bytes=pkt.size,
            msg=hint,
            session_id=session_id,
            world_id=world.world_id,
            network_id=self.host.network_id,
            host_id=self.host.host_id,
            actor=src_actor,
            hostname=src_hostname,
            username=src_username,
            identity_type=src_itype,
        ))

        def arrive(sim2: Simulator, data: tuple[Host, Packet]) -> None:
            dst_host, p = data
            resp = self._deliver(sim2, world, dst_host, p)

            dst_actor, dst_hostname, dst_username, dst_itype = self._dst_identity(dst_host)

            sim2.emit(LogEvent(
                t=sim2.t,
                device=f"host:{dst_host.host_id}",
                event_type="RX",
                src_ip=p.src_ip, dst_ip=p.dst_ip,
                proto=p.proto, src_port=p.src_port, dst_port=p.dst_port,
                result="info",
                bytes=p.size,
                msg=hint,
                session_id=p.session_id,
                world_id=world.world_id,
                network_id=dst_host.network_id,
                host_id=dst_host.host_id,
                actor=dst_actor,
                hostname=dst_hostname,
                username=dst_username,
                identity_type=dst_itype,
                extra={"resp": resp}
            ))

        sim.schedule(sim.t + delay, "ARRIVE", arrive, (dst, pkt))

    # ---------------- ticks ----------------

    def _tick_dns(self, sim: Simulator, data: tuple[World]) -> None:
        (world,) = data
        dst = self._pick_target(world, "DNS", prefer_network_ids=["DMZ", "HQ_DC"])
        if dst:
            q = pick(["guleckargo.com", "track.guleckargo.com", "api.guleckargo.com", "cdn.gulec.net"])
            self._send(sim, world, dst, PROTO_UDP, 53, {"q": q}, size=120, hint="ext_dns_query")
        sim.schedule(sim.t + expovariate(self.p.dns_rate), "TIMER", self._tick_dns, data)

    def _tick_http(self, sim: Simulator, data: tuple[World]) -> None:
        (world,) = data
        dst = self._pick_target(world, "HTTP", prefer_network_ids=["DMZ"])
        if dst:
            if self.p.kind == "partner":
                path = pick(["/api/track", "/api/create_shipment", "/api/status", "/api/pod"])
                hint = "ext_http_api"
            else:
                path = pick(["/track", "/login", "/rates", "/branches", "/help"])
                hint = "ext_http_portal"
            self._send(sim, world, dst, PROTO_TCP, 443, {"path": path}, size=900, hint=hint)
        sim.schedule(sim.t + expovariate(self.p.http_rate), "TIMER", self._tick_http, data)

    def _tick_auth(self, sim: Simulator, data: tuple[World]) -> None:
        (world,) = data
        dst = self._pick_target(world, "AUTH", prefer_network_ids=["DMZ", "HQ_DC"])
        if dst:
            user = pick(["administrator", "user", "operator"])
            if chance(self.p.auth_error_rate):
                pw = pick(["000000", "111111", "123123", "654321", "password", "qwerty"])
            else:
                pw = "123456" if user == "administrator" else "password"

            hint = "ext_auth_attempt" if self.p.kind != "attacker" else "ext_auth_bruteforce"
            self._send(sim, world, dst, PROTO_TCP, 3389, {"username": user, "password": pw}, size=220, hint=hint)
        sim.schedule(sim.t + expovariate(self.p.auth_rate), "TIMER", self._tick_auth, data)

    def _tick_file(self, sim: Simulator, data: tuple[World]) -> None:
        (world,) = data
        if self.p.exfil_chance <= 0:
            sim.schedule(sim.t + expovariate(self.p.file_rate), "TIMER", self._tick_file, data)
            return

        dst = self._pick_target(world, "FILE", prefer_network_ids=["HQ_DC"])
        if dst and chance(self.p.exfil_chance):
            size_mb = rand_int(5, 10)
            size = size_mb * 1024 * 1024
            path = f"/uploads/ext_{self.host.host_id}_{rand_int(1, 9999)}.bin"
            self._send(
                sim, world, dst, PROTO_TCP, 445,
                {"action": "PUT_META", "path": path, "size": size, "hash": "virtual"},
                size=800, hint="ext_file_put_meta"
            )

        sim.schedule(sim.t + expovariate(self.p.file_rate), "TIMER", self._tick_file, data)

    def _tick_scan(self, sim: Simulator, data: tuple[World]) -> None:
        (world,) = data
        candidates = [h for h in world.registry.hosts.values() if h.network_id in ("DMZ", "HQ_DC")]
        if not candidates:
            candidates = list(world.registry.hosts.values())
        dst = random.choice(candidates)
        port = pick([22, 80, 443, 445, 3389, 53, 123, 8080, 3306, 1433])
        proto = PROTO_TCP if port != 53 else PROTO_UDP
        self._send(sim, world, dst, proto, port, {"probe": True}, size=60, hint="ext_scan_probe")
        sim.schedule(sim.t + expovariate(self.p.scan_rate), "TIMER", self._tick_scan, data)

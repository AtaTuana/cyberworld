from __future__ import annotations

import random
from typing import Any, Dict, Optional

from engine.sim import Simulator
from telemetry.log_event import LogEvent
from core.ids import next_session_id
from core.rng import chance, rand_int, pick
from core.constants import PROTO_TCP, PROTO_UDP

from net.packet import Packet
from world.world import World
from host.host import Host
from agents.behavior import Behavior


def expovariate(rate: float) -> float:
    if rate <= 0:
        return 1e18
    return random.expovariate(rate)


class ClientAgent:
    def __init__(self, host: Host, behavior: Behavior) -> None:
        self.host = host
        self.behavior = behavior

    def start(self, sim: Simulator, world: World) -> None:
        sim.schedule(sim.t + expovariate(self.behavior.dns_rate),  "TIMER", self._tick_dns,  (world,))
        sim.schedule(sim.t + expovariate(self.behavior.http_rate), "TIMER", self._tick_http, (world,))
        sim.schedule(sim.t + expovariate(self.behavior.auth_rate), "TIMER", self._tick_auth, (world,))
        sim.schedule(sim.t + expovariate(self.behavior.file_rate), "TIMER", self._tick_file, (world,))
        if self.behavior.scan_rate > 0:
            sim.schedule(sim.t + expovariate(self.behavior.scan_rate), "TIMER", self._tick_scan, (world,))

    def _pick_server(self, world: World, service_name: str) -> Optional[Host]:
        candidates = [h for h in world.registry.hosts.values() if h.has_service(service_name)]
        if not candidates:
            return None
        return random.choice(candidates)

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

    def _send(self, sim: Simulator, world: World, dst: Host, proto: str, dst_port: int,
              payload: Dict[str, Any], size: int, hint: str) -> None:
        topo = world.registry.topology
        assert topo is not None

        session_id = next_session_id("sess_")
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
        ))

        def arrive(sim2: Simulator, data: tuple[Host, Packet]) -> None:
            dst_host, p = data
            resp = self._deliver(sim2, world, dst_host, p)
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
                extra={"resp": resp}
            ))

        sim.schedule(sim.t + delay, "ARRIVE", arrive, (dst, pkt))

    def _tick_dns(self, sim: Simulator, data: tuple[World]) -> None:
        (world,) = data
        dst = self._pick_server(world, "DNS")
        if dst:
            q = pick(["example.com", "cdn.net", "uni.edu", "bank.com", "updates.local"])
            self._send(sim, world, dst, PROTO_UDP, 53, {"q": q}, size=120, hint="dns_query")
        sim.schedule(sim.t + expovariate(self.behavior.dns_rate), "TIMER", self._tick_dns, data)

    def _tick_http(self, sim: Simulator, data: tuple[World]) -> None:
        (world,) = data
        dst = self._pick_server(world, "HTTP")
        if dst:
            path = pick(["/", "/login", "/assets/app.js", "/api/data", "/health"])
            self._send(sim, world, dst, PROTO_TCP, 443, {"path": path}, size=900, hint="http_get")
        sim.schedule(sim.t + expovariate(self.behavior.http_rate), "TIMER", self._tick_http, data)

    def _tick_auth(self, sim: Simulator, data: tuple[World]) -> None:
        (world,) = data
        dst = self._pick_server(world, "AUTH")
        if dst:
            user = pick(["administrator", "user"])
            if chance(self.behavior.auth_error_rate):
                pw = pick(["000000", "111111", "password", "123123", "654321"])
            else:
                pw = "123456" if user == "administrator" else "password"
            self._send(sim, world, dst, PROTO_TCP, 3389,
                       {"username": user, "password": pw}, size=220, hint="auth_attempt")
        sim.schedule(sim.t + expovariate(self.behavior.auth_rate), "TIMER", self._tick_auth, data)

    def _tick_file(self, sim: Simulator, data: tuple[World]) -> None:
        (world,) = data
        dst = self._pick_server(world, "FILE")
        if dst and chance(self.behavior.exfil_chance):
            size_mb = rand_int(5, 10)
            size = size_mb * 1024 * 1024
            path = f"/uploads/{self.host.host_id}_{rand_int(1, 9999)}.bin"
            self._send(sim, world, dst, PROTO_TCP, 445,
                       {"action": "PUT_META", "path": path, "size": size, "hash": "virtual"},
                       size=800, hint="file_put_meta")
        sim.schedule(sim.t + expovariate(self.behavior.file_rate), "TIMER", self._tick_file, data)

    def _tick_scan(self, sim: Simulator, data: tuple[World]) -> None:
        (world,) = data
        dst = random.choice(list(world.registry.hosts.values()))
        port = pick([22, 80, 443, 445, 3389, 53, 123, 8080, 3306])
        proto = PROTO_TCP if port != 53 else PROTO_UDP
        self._send(sim, world, dst, proto, port, {"probe": True}, size=60, hint="scan_probe")
        sim.schedule(sim.t + expovariate(self.behavior.scan_rate), "TIMER", self._tick_scan, data)

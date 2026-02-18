from __future__ import annotations

import random
import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from telemetry.sinks import Sink
from net.link import Link
from net.packet import Packet


@dataclass
class CoreRouter:
    rid: str
    neighbors: Dict[str, Link] = field(default_factory=dict)


class Topology:
    """
    Graph-like "internet core" + per-network uplinks.

    We route by network_id for scale:
      src_host.network_id -> dst_host.network_id
    """
    def __init__(self, core_routers: int, sink: Sink, world_id: str) -> None:
        self.world_id = world_id
        self.sink = sink

        self.core: Dict[str, CoreRouter] = {}
        self.core_ids: List[str] = [f"ASR{i}" for i in range(core_routers)]
        for rid in self.core_ids:
            self.core[rid] = CoreRouter(rid=rid)

        # ensure connectivity with a chain
        for i in range(len(self.core_ids) - 1):
            self._link(self.core_ids[i], self.core_ids[i + 1], self._core_link())

        # add some random mesh edges
        for i in range(len(self.core_ids)):
            for j in range(i + 1, len(self.core_ids)):
                if random.random() < 0.10:
                    self._link(self.core_ids[i], self.core_ids[j], self._core_link())

        # network_id -> attached core gateway router
        self.net_gateway: Dict[str, str] = {}
        self.net_uplink: Dict[str, Link] = {}   # network_id -> uplink link
        self.host_to_net: Dict[str, str] = {}   # host_id -> network_id
        self.host_ip: Dict[str, str] = {}       # host_id -> ip

    def _core_link(self) -> Link:
        return Link(
            bandwidth_bytes_per_sec=random.randint(8_000_000, 50_000_000),
            latency_ms=random.randint(10, 70),
            loss=random.uniform(0.00005, 0.001),
            jitter_ms=7,
        )

    def _link(self, a: str, b: str, lk: Link) -> None:
        self.core[a].neighbors[b] = lk
        self.core[b].neighbors[a] = lk

    def attach_host(self, host, net_spec) -> None:
        self.host_to_net[host.host_id] = net_spec.network_id
        self.host_ip[host.host_id] = host.ip

        if net_spec.network_id not in self.net_gateway:
            gw = random.choice(self.core_ids)
            self.net_gateway[net_spec.network_id] = gw
            self.net_uplink[net_spec.network_id] = Link(
                bandwidth_bytes_per_sec=net_spec.bandwidth_bps,
                latency_ms=net_spec.latency_ms,
                loss=net_spec.loss,
                jitter_ms=8,
            )

    def shortest_path(self, src_router: str, dst_router: str) -> List[str]:
        if src_router == dst_router:
            return [src_router]

        dist: Dict[str, float] = {src_router: 0.0}
        prev: Dict[str, str] = {}
        pq: List[Tuple[float, str]] = [(0.0, src_router)]

        while pq:
            d, u = heapq.heappop(pq)
            if u == dst_router:
                break
            if d != dist.get(u, 1e18):
                continue
            for v, lk in self.core[u].neighbors.items():
                nd = d + lk.latency_ms
                if nd < dist.get(v, 1e18):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))

        if dst_router != src_router and dst_router not in prev:
            return [src_router, dst_router]

        path = [dst_router]
        cur = dst_router
        while cur != src_router:
            cur = prev[cur]
            path.append(cur)
        path.reverse()
        return path

    def route_packet_delay(self, pkt: Packet, src_network: str, dst_network: str) -> tuple[float, List[str], str]:
        """
        Returns (total_delay_sec, hop_routers, outcome)
          outcome: "ok" | "drop_uplink" | "drop_core"
        """
        src_gw = self.net_gateway[src_network]
        dst_gw = self.net_gateway[dst_network]

        uplink_src = self.net_uplink[src_network]
        total = 0.0

        if uplink_src.should_drop():
            return (uplink_src.delay_sec(pkt.size), [], "drop_uplink")
        total += uplink_src.delay_sec(pkt.size)

        path = self.shortest_path(src_gw, dst_gw)
        for i in range(len(path) - 1):
            a = path[i]
            b = path[i + 1]
            lk = self.core[a].neighbors[b]
            if lk.should_drop():
                total += lk.delay_sec(pkt.size)
                return (total, path[: i + 1], "drop_core")
            total += lk.delay_sec(pkt.size)

        uplink_dst = self.net_uplink[dst_network]
        if uplink_dst.should_drop():
            total += uplink_dst.delay_sec(pkt.size)
            return (total, path, "drop_uplink")
        total += uplink_dst.delay_sec(pkt.size)

        return (total, path, "ok")

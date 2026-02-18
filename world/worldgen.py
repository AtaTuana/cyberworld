from __future__ import annotations

import os
import json
from typing import List, Tuple

from engine.sim import Simulator
from core.ids import next_entity_id
from core.rng import weighted_choice, rand_int, rand_float, chance

from world.world import World, NetworkSpec
from world.registry import Registry

from net.topology import Topology

from host.host import Host
from host.disk import VirtualDisk
from host.users import UserDB

from services.auth import AuthService
from services.dns import DnsService
from services.http import HttpService
from services.filetransfer import FileService


def _weights_from_profiles(profiles: dict) -> Tuple[List[str], List[float]]:
    items: List[str] = []
    weights: List[float] = []
    for k, v in profiles["network_types"].items():
        items.append(k)
        weights.append(float(v["weight"]))
    return items, weights


def _network_size(kind: str) -> int:
    if kind == "home":
        return rand_int(3, 12)
    if kind == "smb":
        return rand_int(15, 60)
    if kind == "enterprise":
        return rand_int(60, 140)
    if kind == "campus":
        return rand_int(40, 120)
    if kind == "cloud":
        return rand_int(10, 40)
    if kind == "iot":
        return rand_int(15, 80)
    return rand_int(5, 25)


def _uplink_params(kind: str) -> tuple[int, int, float]:
    # bandwidth is bytes/sec (sim), not bits
    if kind == "home":
        return rand_int(2_000_000, 8_000_000), rand_int(15, 40), rand_float(0.0005, 0.004)
    if kind == "smb":
        return rand_int(5_000_000, 20_000_000), rand_int(8, 25), rand_float(0.0002, 0.002)
    if kind == "enterprise":
        return rand_int(15_000_000, 80_000_000), rand_int(3, 15), rand_float(0.0001, 0.001)
    if kind == "campus":
        return rand_int(10_000_000, 50_000_000), rand_int(4, 18), rand_float(0.0001, 0.002)
    if kind == "cloud":
        return rand_int(20_000_000, 120_000_000), rand_int(1, 10), rand_float(0.00005, 0.001)
    if kind == "iot":
        return rand_int(3_000_000, 12_000_000), rand_int(8, 35), rand_float(0.0003, 0.004)
    return rand_int(3_000_000, 10_000_000), rand_int(10, 30), rand_float(0.0005, 0.003)


def _alloc_ip(network_index: int, host_index: int) -> str:
    # 10.<net>.<block>.<host>
    a = 10
    b = (network_index % 250) + 1
    c = (host_index // 250) % 250
    d = (host_index % 250) + 1
    return f"{a}.{b}.{c}.{d}"


def _host_role(kind: str) -> str:
    r = rand_float(0.0, 1.0)
    if kind == "home":
        return "server" if r < 0.05 else ("iot" if r < 0.25 else "client")
    if kind == "smb":
        return "server" if r < 0.18 else "client"
    if kind == "enterprise":
        return "server" if r < 0.10 else "client"
    if kind == "campus":
        return "server" if r < 0.06 else "client"
    if kind == "cloud":
        return "server" if r < 0.80 else "client"
    if kind == "iot":
        return "iot" if r < 0.75 else ("server" if r < 0.80 else "client")
    return "client"


def _assign_services(role: str, kind: str) -> list[str]:
    svcs: list[str] = []
    if role == "server":
        if chance(0.55):
            svcs.append("HTTP")
        if chance(0.35):
            svcs.append("DNS")
        if chance(0.25):
            svcs.append("FILE")
        if chance(0.18):
            svcs.append("AUTH")

        if kind in ("enterprise", "campus") and chance(0.35):
            svcs.append("AUTH")
        if kind in ("enterprise", "smb") and chance(0.45):
            svcs.append("FILE")

        return sorted(list(set(svcs)))

    if role == "iot":
        if chance(0.20):
            svcs.append("HTTP")
        return svcs

    return svcs


def generate_world(sim: Simulator, cfg: dict, profiles: dict, out_dir: str) -> World:
    world_id = next_entity_id("world_")

    networks_target = int(cfg["world"]["networks_target"])
    hosts_target = int(cfg["world"]["hosts_target"])
    core_routers = int(cfg["world"]["core_routers"])

    net_types, net_w = _weights_from_profiles(profiles)

    # --- Build network specs with budget
    networks: list[NetworkSpec] = []
    remaining_hosts = hosts_target

    for i in range(networks_target):
        kind = weighted_choice(net_types, net_w)
        size = _network_size(kind)

        # clamp so we don't run out before finishing all networks
        if i == networks_target - 1:
            size = max(1, remaining_hosts)
        else:
            min_left = (networks_target - i - 1)
            size = min(size, max(1, remaining_hosts - min_left))

        remaining_hosts -= size

        bw, lat, loss = _uplink_params(kind)
        nid = next_entity_id("net_")
        networks.append(NetworkSpec(
            network_id=nid,
            kind=kind,
            size=size,
            bandwidth_bps=bw,
            latency_ms=lat,
            loss=loss
        ))

    registry = Registry()
    topo = Topology(core_routers=core_routers, sink=sim.sink, world_id=world_id)
    registry.topology = topo

    # --- Create hosts
    disk_dir = os.path.join(out_dir, "disks")
    os.makedirs(disk_dir, exist_ok=True)

    for net_index, ns in enumerate(networks):
        for j in range(ns.size):
            role = _host_role(ns.kind)
            service_names = _assign_services(role, ns.kind)

            host_id = next_entity_id("host_")
            ip = _alloc_ip(net_index, j + 1)

            # capacity is metadata-only
            if role == "server":
                cap_gb = rand_int(50, 500)
            elif role == "iot":
                cap_gb = rand_int(1, 8)
            else:
                cap_gb = rand_int(10, 80)

            disk_path = os.path.join(disk_dir, f"{host_id}.json")
            disk = VirtualDisk(path=disk_path, capacity_bytes=cap_gb * 1024**3)
            disk.seed_files()

            users = UserDB()
            users.add_user("administrator", "123456", is_admin=True)
            if chance(0.25):
                users.add_user("user", "password", is_admin=False)

            h = Host(
                host_id=host_id,
                ip=ip,
                network_id=ns.network_id,
                role=role,
                disk=disk,
                users=users,
                world_id=world_id
            )

            for s in service_names:
                if s == "DNS":
                    h.add_service(DnsService())
                elif s == "HTTP":
                    h.add_service(HttpService())
                elif s == "AUTH":
                    h.add_service(AuthService(lockout_threshold=25))
                elif s == "FILE":
                    h.add_service(FileService())

            registry.add_host(h)
            topo.attach_host(h, ns)

    # --- Save world snapshot
    worlds_dir = os.path.join(out_dir, "worlds")
    os.makedirs(worlds_dir, exist_ok=True)
    world_path = os.path.join(worlds_dir, f"{world_id}.json")

    with open(world_path, "w", encoding="utf-8") as f:
        json.dump({
            "world_id": world_id,
            "seed": sim.seed,
            "networks": [ns.__dict__ for ns in networks],
            "hosts": [{
                "host_id": h.host_id,
                "ip": h.ip,
                "network_id": h.network_id,
                "role": h.role,
                "services": list(h.services.keys()),
                "disk_path": h.disk.path
            } for h in registry.hosts.values()]
        }, f, ensure_ascii=False, indent=2)

    return World(world_id=world_id, networks=networks, registry=registry, meta={"world_path": world_path})

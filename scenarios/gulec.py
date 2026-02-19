from __future__ import annotations

import os
import json
import random

from engine.sim import Simulator
from core.ids import next_entity_id
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

from identity.identity_factory import IdentityFactory


def build(sim: Simulator, cfg: dict, profiles: dict, out_dir: str) -> World:
    world_id = "gulec_kargo_world"

    registry = Registry()
    topo = Topology(core_routers=40, sink=sim.sink, world_id=world_id)
    registry.topology = topo

    idf = IdentityFactory(sim.seed, org_prefix="GK")

    networks: list[NetworkSpec] = []

    # INTERNET
    internet_net = NetworkSpec(
        network_id="INTERNET",
        kind="cloud",
        size=30,
        bandwidth_bps=120_000_000,
        latency_ms=20,
        loss=0.0003,
    )
    networks.append(internet_net)

    # HQ
    hq_net = NetworkSpec(
        network_id="HQ_DC",
        kind="enterprise",
        size=200,
        bandwidth_bps=80_000_000,
        latency_ms=5,
        loss=0.0001,
    )
    networks.append(hq_net)

    # DMZ
    dmz_net = NetworkSpec(
        network_id="DMZ",
        kind="enterprise",
        size=20,
        bandwidth_bps=50_000_000,
        latency_ms=8,
        loss=0.0002,
    )
    networks.append(dmz_net)

    # Regions
    for i in range(5):
        networks.append(NetworkSpec(
            network_id=f"REGION_{i}",
            kind="enterprise",
            size=80,
            bandwidth_bps=30_000_000,
            latency_ms=10,
            loss=0.0003,
        ))

    # Branches
    for i in range(20):
        networks.append(NetworkSpec(
            network_id=f"BRANCH_{i}",
            kind="smb",
            size=25,
            bandwidth_bps=10_000_000,
            latency_ms=15,
            loss=0.001,
        ))

    # Warehouses
    for i in range(6):
        networks.append(NetworkSpec(
            network_id=f"WAREHOUSE_{i}",
            kind="iot",
            size=60,
            bandwidth_bps=15_000_000,
            latency_ms=12,
            loss=0.0008,
        ))

    # Cloud segment
    cloud_net = NetworkSpec(
        network_id="CLOUD",
        kind="cloud",
        size=15,
        bandwidth_bps=100_000_000,
        latency_ms=3,
        loss=0.00005,
    )
    networks.append(cloud_net)

    # disks
    disk_dir = os.path.join(out_dir, "disks")
    os.makedirs(disk_dir, exist_ok=True)

    def create_host(
        net: NetworkSpec,
        role: str,
        services: list[str],
        ip: str | None = None,
        capacity_gb: int = 100
    ) -> Host:
        host_id = next_entity_id("gk_host_")

        if ip is None:
            ip = f"10.{random.randint(1,250)}.{random.randint(0,250)}.{random.randint(1,250)}"

        disk = VirtualDisk(
            path=os.path.join(disk_dir, f"{host_id}.json"),
            capacity_bytes=capacity_gb * 1024**3,
        )
        disk.seed_files()

        users = UserDB()
        users.add_user("administrator", "123456", True)
        users.add_user("operator", "password", False)
        if random.random() < 0.4:
            users.add_user("user", "password", False)

        h = Host(
            host_id=host_id,
            ip=ip,
            network_id=net.network_id,
            role=role,
            disk=disk,
            users=users,
            world_id=world_id,
        )

        for s in services:
            if s == "DNS":
                h.add_service(DnsService())
            elif s == "HTTP":
                h.add_service(HttpService())
            elif s == "AUTH":
                h.add_service(AuthService(lockout_threshold=20))
            elif s == "FILE":
                h.add_service(FileService())

        # ---------- Identity assignment ----------
        if role == "server":
            if "DNS" in services:
                ident = idf.system_server("dns")
            elif "AUTH" in services:
                ident = idf.system_server("auth")
            elif "FILE" in services:
                ident = idf.system_server("file")
            elif "HTTP" in services:
                ident = idf.system_server("web")
            else:
                ident = idf.system_server("app")

        elif role == "iot":
            wh_label = net.network_id.replace("WAREHOUSE_", "WH")
            ident = idf.warehouse_device(wh_label)

        elif role == "external":
            ident = idf.person(hostname=f"HOME-PC-{random.randint(100,999)}")

        else:
            if net.network_id.startswith("BRANCH_"):
                ident = idf.branch_user(net.network_id.replace("BRANCH_", "BR"))
            else:
                ident = idf.person()

        # Host’a attribute olarak bas (Host classını değiştirmeden)
        h.display_name = ident.display_name
        h.username = ident.username
        h.hostname = ident.hostname
        h.identity_type = ident.identity_type

        registry.add_host(h)
        topo.attach_host(h, net)
        return h

    # HQ services
    create_host(hq_net, "server", ["DNS", "AUTH", "FILE"])
    create_host(hq_net, "server", ["HTTP"])
    create_host(hq_net, "server", ["FILE"])

    # DMZ
    create_host(dmz_net, "server", ["HTTP"])
    create_host(dmz_net, "server", ["AUTH"])
    create_host(dmz_net, "server", ["DNS"])

    # Sites
    for net in networks:
        if net.network_id.startswith("REGION_") or net.network_id.startswith("BRANCH_"):
            for _ in range(10):
                create_host(net, "client", [])

        if net.network_id.startswith("WAREHOUSE_"):
            for _ in range(30):
                create_host(net, "iot", [])

        if net.network_id == "CLOUD":
            for _ in range(5):
                create_host(net, "server", ["HTTP"])

    # External 30
    external_hosts: list[Host] = []
    for _ in range(30):
        pub_ip = f"185.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        h = create_host(internet_net, role="external", services=[], ip=pub_ip, capacity_gb=5)
        external_hosts.append(h)

    # Snapshot
    worlds_dir = os.path.join(out_dir, "worlds")
    os.makedirs(worlds_dir, exist_ok=True)
    world_path = os.path.join(worlds_dir, f"{world_id}.json")

    with open(world_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "world_id": world_id,
                "seed": sim.seed,
                "networks": [n.__dict__ for n in networks],
                "hosts": [
                    {
                        "host_id": h.host_id,
                        "ip": h.ip,
                        "network_id": h.network_id,
                        "role": h.role,
                        "services": list(h.services.keys()),
                        "display_name": getattr(h, "display_name", h.host_id),
                        "hostname": getattr(h, "hostname", "-"),
                        "username": getattr(h, "username", "-"),
                        "identity_type": getattr(h, "identity_type", "-"),
                        "disk_path": h.disk.path,
                    }
                    for h in registry.hosts.values()
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return World(
        world_id=world_id,
        networks=networks,
        registry=registry,
        meta={
            "world_path": world_path,
            "external_host_ids": [h.host_id for h in external_hosts],
        },
    )


def schedule(sim: Simulator, world: World, cfg: dict, profiles: dict) -> None:
    # Internal traffic
    from agents.workload import schedule_world_workloads
    schedule_world_workloads(sim, world, cfg, profiles)

    # External actors
    from agents.external_actor import ExternalActorAgent, ExternalProfile
    from identity.identity_factory import IdentityFactory

    idf = IdentityFactory(sim.seed, org_prefix="GK")

    ext_ids = world.meta.get("external_host_ids", [])
    if not ext_ids:
        return

    kinds = (["customer"] * 12 + ["partner"] * 6 + ["remote"] * 6 + ["attacker"] * 6)
    random.shuffle(kinds)

    for hid, kind in zip(ext_ids, kinds):
        h = world.registry.get_host(hid)

        # attacker ise kimliği değiştirelim (fake/bot/service)
        if kind == "attacker":
            ident = idf.attacker()
            h.display_name = ident.display_name
            h.username = ident.username
            h.hostname = ident.hostname
            h.identity_type = ident.identity_type

        if kind == "customer":
            prof = ExternalProfile(kind=kind, dns_rate=0.08, http_rate=0.25, auth_rate=0.01, scan_rate=0.0, file_rate=0.0, auth_error_rate=0.15)
        elif kind == "partner":
            prof = ExternalProfile(kind=kind, dns_rate=0.05, http_rate=0.18, auth_rate=0.005, scan_rate=0.0, file_rate=0.0, auth_error_rate=0.10)
        elif kind == "remote":
            prof = ExternalProfile(kind=kind, dns_rate=0.02, http_rate=0.03, auth_rate=0.06, scan_rate=0.0, file_rate=0.0, auth_error_rate=0.12)
        else:
            prof = ExternalProfile(kind=kind, dns_rate=0.02, http_rate=0.05, auth_rate=0.35, scan_rate=0.50, file_rate=0.03, auth_error_rate=0.98, exfil_chance=0.25)

        ExternalActorAgent(host=h, profile=prof).start(sim, world)

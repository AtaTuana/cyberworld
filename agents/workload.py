from __future__ import annotations

import random
from typing import Dict

from core.rng import rand_float
from agents.behavior import Behavior
from agents.client_agent import ClientAgent
from world.world import World


def _base_rates(cfg: dict, net_kind: str) -> dict:
    return cfg["traffic"].get(net_kind, cfg["traffic"]["home"])


def schedule_world_workloads(sim, world: World, cfg: dict, profiles: dict) -> None:
    """
    Assign each host a realistic behavior based on its network kind + role.
    Inject 2–8% anomaly hosts by adjusting behavior params (still no explicit "attack" label).
    """
    net_kind_by_id = {n.network_id: n.kind for n in world.networks}
    hosts = list(world.registry.hosts.values())

    anomaly_ratio = rand_float(0.02, 0.08)
    anomaly_count = max(1, int(len(hosts) * anomaly_ratio))
    anomaly_hosts = set(h.host_id for h in random.sample(hosts, anomaly_count))

    for h in hosts:
        kind = net_kind_by_id[h.network_id]
        base = _base_rates(cfg, kind)

        if h.role == "server":
            scale = 0.6
        elif h.role == "iot":
            scale = 0.7
        else:
            scale = 1.0

        dns = float(base["dns"]) * scale
        http = float(base["http"]) * scale
        auth = float(base["auth"]) * scale
        file = float(base["file"]) * scale

        # host-level jitter
        jitter = rand_float(0.6, 1.4)
        dns *= jitter
        http *= jitter
        auth *= jitter
        file *= jitter

        beh = Behavior(dns_rate=dns, http_rate=http, auth_rate=auth, file_rate=file)

        if h.host_id in anomaly_hosts:
            r = rand_float(0.0, 1.0)
            if r < 0.35:
                # brute-force-ish
                beh.auth_rate *= 80
                beh.auth_error_rate = 0.98
            elif r < 0.65:
                # scan-ish
                beh.scan_rate = 0.8
            else:
                # exfil-ish
                beh.exfil_chance = 0.35
                beh.file_rate *= 8

        ClientAgent(host=h, behavior=beh).start(sim, world)

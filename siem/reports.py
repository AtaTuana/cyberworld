from __future__ import annotations

from typing import List, Dict, Any
from world.world import World


def print_report(world: World, log_path: str, alerts: List[Dict[str, Any]]) -> None:
    print("\n" + "=" * 90)
    print("CYBERWORLD REPORT")
    print("=" * 90)
    print(f"World: {world.world_id}")
    print(f"World snapshot: {world.meta.get('world_path')}")
    print(f"Log: {log_path}")
    print(f"Networks: {len(world.networks)}")
    print(f"Hosts: {len(world.registry.hosts)}")

    kind_count: Dict[str, int] = {}
    for n in world.networks:
        kind_count[n.kind] = kind_count.get(n.kind, 0) + 1

    print("\nNetwork kinds:")
    for k, v in sorted(kind_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k:<10} : {v}")

    svc_count: Dict[str, int] = {}
    for h in world.registry.hosts.values():
        for s in h.services.keys():
            svc_count[s] = svc_count.get(s, 0) + 1

    print("\nService distribution:")
    for k, v in sorted(svc_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k:<6} : {v}")

    print("\nAlerts:")
    if not alerts:
        print("  (none)")
    else:
        for a in alerts:
            print(f"  - {a}")

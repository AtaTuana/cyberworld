from __future__ import annotations

from typing import Callable, Tuple

from engine.sim import Simulator
from world.world import World

# types
BuildFn = Callable[[Simulator, dict, dict, str], World]
ScheduleFn = Callable[[Simulator, World, dict, dict], None]


def _random_build(sim: Simulator, cfg: dict, profiles: dict, out_dir: str) -> World:
    from world.worldgen import generate_world
    return generate_world(sim=sim, cfg=cfg, profiles=profiles, out_dir=out_dir)


def _random_schedule(sim: Simulator, world: World, cfg: dict, profiles: dict) -> None:
    from agents.workload import schedule_world_workloads
    schedule_world_workloads(sim=sim, world=world, cfg=cfg, profiles=profiles)


# ✅ BURASI ÖNEMLİ: gulec'i import et
from scenarios import gulec  # scenarios/gulec.py


SCENARIOS: dict[str, Tuple[BuildFn, ScheduleFn]] = {
    "random": (_random_build, _random_schedule),
    "gulec": (gulec.build, gulec.schedule),
}

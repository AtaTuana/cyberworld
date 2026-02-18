from __future__ import annotations

import os
import time
import yaml

from engine.sim import Simulator
from telemetry.sinks import JsonlFileSink, MultiSink
from world.worldgen import generate_world
from agents.workload import schedule_world_workloads
from siem.detectors import run_detectors
from siem.reports import print_report


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    cfg = load_yaml("config/default.yaml")
    profiles = load_yaml("config/profiles.yaml")

    seed = int(cfg.get("seed", 42))
    duration = float(cfg["sim"]["duration_sec"])
    max_events = int(cfg["sim"]["max_events"])

    os.makedirs("data/worlds", exist_ok=True)
    os.makedirs("data/disks", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)

    ts = int(time.time())
    log_path = f"data/logs/run_{seed}_{ts}.jsonl"

    sink = MultiSink([JsonlFileSink(log_path)])

    sim = Simulator(seed=seed, sink=sink)

    world = generate_world(sim=sim, cfg=cfg, profiles=profiles, out_dir="data")

    schedule_world_workloads(sim=sim, world=world, cfg=cfg, profiles=profiles)

    sim.run(t_end=duration, max_events=max_events)

    sink.close()

    alerts = run_detectors(log_path)
    print_report(world=world, log_path=log_path, alerts=alerts)


if __name__ == "__main__":
    main()

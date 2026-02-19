from __future__ import annotations

import os
import time
import yaml
import argparse

from engine.sim import Simulator
from telemetry.sinks import JsonlFileSink, MultiSink
from siem.detectors import run_detectors
from siem.reports import print_report
from scenarios.registry import SCENARIOS


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="random", help="Scenario name (default: random)")
    parser.add_argument("--seed", type=int, default=None, help="Override seed from config")
    args = parser.parse_args()

    cfg = load_yaml("config/default.yaml")
    profiles = load_yaml("config/profiles.yaml")

    seed = args.seed if args.seed is not None else int(cfg.get("seed", 42))
    duration = float(cfg["sim"]["duration_sec"])
    max_events = int(cfg["sim"]["max_events"])

    os.makedirs("data/worlds", exist_ok=True)
    os.makedirs("data/disks", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)

    ts = int(time.time())
    log_path = f"data/logs/run_{args.scenario}_{seed}_{ts}.jsonl"

    sink = MultiSink([JsonlFileSink(log_path)])
    sim = Simulator(seed=seed, sink=sink)

    if args.scenario not in SCENARIOS:
        raise SystemExit(f"Unknown scenario: {args.scenario}. Available: {', '.join(SCENARIOS.keys())}")

    build_fn, schedule_fn = SCENARIOS[args.scenario]

    world = build_fn(sim, cfg, profiles, out_dir="data")
    schedule_fn(sim, world, cfg, profiles)

    sim.run(t_end=duration, max_events=max_events)
    sink.close()

    alerts = run_detectors(log_path)
    print_report(world=world, log_path=log_path, alerts=alerts)


if __name__ == "__main__":
    main()

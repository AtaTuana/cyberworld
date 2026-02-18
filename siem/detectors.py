from __future__ import annotations

from collections import defaultdict, Counter
from typing import Dict, Any, List

from siem.query import iter_jsonl


def run_detectors(log_path: str) -> List[Dict[str, Any]]:
    """
    v1 detectors (heuristics):
      - bruteforce_suspected: >= 30 auth fails from same src_ip
      - portscan_suspected: >= 10 unique dst_port from same src_ip (scan_probe)
      - exfil_suspected: >= 5 successful file_put_meta events from same src_ip
    """
    alerts: List[Dict[str, Any]] = []

    auth_fail = Counter()
    scan_ports = defaultdict(set)
    file_put_ok = Counter()

    for e in iter_jsonl(log_path):
        msg = e.get("msg")
        src = e.get("src_ip", "-")
        dport = int(e.get("dst_port", 0))
        extra = e.get("extra") or {}
        resp = extra.get("resp") if isinstance(extra, dict) else None

        # bruteforce-ish: based on auth_attempt response
        if msg == "auth_attempt" and isinstance(resp, dict):
            if resp.get("ok") is False and resp.get("reason") in ("bad_password", "locked_out"):
                auth_fail[src] += 1

        # scan-ish
        if msg == "scan_probe":
            scan_ports[src].add(dport)

        # exfil-ish
        if msg == "file_put_meta" and isinstance(resp, dict) and resp.get("ok") is True:
            file_put_ok[src] += 1

    for src, n in auth_fail.items():
        if n >= 30:
            alerts.append({"type": "bruteforce_suspected", "src_ip": src, "fails": n})

    for src, ports in scan_ports.items():
        if len(ports) >= 10:
            alerts.append({
                "type": "portscan_suspected",
                "src_ip": src,
                "unique_ports": len(ports),
                "ports_sample": sorted(list(ports))[:25],
            })

    for src, n in file_put_ok.items():
        if n >= 5:
            alerts.append({"type": "exfil_suspected", "src_ip": src, "file_put_events": n})

    return alerts

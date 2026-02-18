## Features
- 20 randomized networks
- ~200 hosts
- Virtual disk metadata (no large allocations)
- Simulated routing + bandwidth + packet loss
- JSONL telemetry
- Basic SIEM detectors

# cyberworld

Game-like cyber world simulator (NOT real VMs/OS):
- Randomized realistic worldgen (20 networks, ~200 hosts)
- Virtual disks saved as JSON (metadata only, no huge allocations)
- Virtual network (latency/bw/loss) + services (DNS/HTTP/AUTH/FILE)
- JSONL logs for SIEM-style analysis

Run:
```bash
python main.py

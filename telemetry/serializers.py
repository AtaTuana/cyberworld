from __future__ import annotations

import json
from telemetry.log_event import LogEvent


def to_json_line(e: LogEvent) -> str:
    return json.dumps(e.to_dict(), ensure_ascii=False)

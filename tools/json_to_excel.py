import json
import csv
import sys
from pathlib import Path
from typing import Any, Dict


EXCLUDE_COLUMNS = {
    "event_type",
    "world_id",
    "extra",
    "extra_resp_answer",
    "extra_resp_ok",
    "extra_resp_path",
    "extra_resp_reason",
    "extra_resp_status",
}


def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
    """
    Nested dict'leri düzleştirir:
      {"extra":{"resp":{"ok":true}}} -> {"extra_resp_ok": true}
    """
    items: Dict[str, Any] = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key, sep=sep))
        else:
            items[new_key] = v
    return items


def filter_columns(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    İstenmeyen kolonları kaldırır.
    """
    return {k: v for k, v in row.items() if k not in EXCLUDE_COLUMNS}


def convert(jsonl_path: str, output_csv: str) -> None:
    rows = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            flat = flatten_dict(obj)
            filtered = filter_columns(flat)
            rows.append(filtered)

    if not rows:
        print("No data found.")
        return

    # CSV header: tüm satırlardaki key birleşimi
    fieldnames = sorted(set().union(*(r.keys() for r in rows)))

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV oluşturuldu (filtreli): {output_csv}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python tools/jsonl_to_excel.py <logfile.jsonl>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = str(Path(input_path).with_suffix(".csv"))

    convert(input_path, output_path)


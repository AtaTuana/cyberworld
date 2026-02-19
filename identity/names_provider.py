from __future__ import annotations

import random
from pathlib import Path
from typing import List


class NameProvider:
    """
    TXT dosyalarından isim/soyisim okur.
    Seed -> deterministik seçim.
    """
    def __init__(self, seed: int, base_dir: str = "data/names") -> None:
        self.rng = random.Random(seed)
        base = Path(base_dir)

        self.first_names = self._load_lines(base / "first_names.txt") or ["Mehmet"]
        self.last_names = self._load_lines(base / "last_names.txt") or ["Kaya"]

    def _load_lines(self, path: Path) -> List[str]:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    def full_name(self) -> str:
        return f"{self.rng.choice(self.first_names)} {self.rng.choice(self.last_names)}"

    def username_from_name(self, full_name: str) -> str:
        parts = full_name.split()
        if len(parts) < 2:
            return full_name.lower()
        fn, ln = parts[0].lower(), parts[-1].lower()

        # TR karakter normalizasyonu (basit)
        repl = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
        fn = fn.translate(repl)
        ln = ln.translate(repl)

        patterns = [
            f"{fn}.{ln}",
            f"{fn}{ln}",
            f"{fn[0]}{ln}",
            f"{ln}.{fn}",
        ]
        return self.rng.choice(patterns)

    def bot_name(self) -> str:
        samples = [
            "deneme1",
            "scanner-07",
            "botnet_443",
            "xXx_hacker_xXx",
            "svc_backup",
            "unknown_user",
            "tmp_admin",
            "auto_login",
            "probe_3389",
        ]
        return self.rng.choice(samples)

    def service_account(self) -> str:
        samples = [
            "svc_vpn",
            "svc_backup",
            "svc_update",
            "svc_monitor",
            "svc_print",
        ]
        return self.rng.choice(samples)

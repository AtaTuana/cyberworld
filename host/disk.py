from __future__ import annotations

import os
import json
import random
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class FileMeta:
    path: str
    size: int
    kind: str = "blob"
    hash: str = ""


@dataclass
class VirtualDisk:
    """
    Virtual disk that persists ONLY metadata to JSON (no big content).
    """
    path: str
    capacity_bytes: int
    files: Dict[str, FileMeta] = field(default_factory=dict)

    def used_bytes(self) -> int:
        return sum(f.size for f in self.files.values())

    def can_store(self, size: int) -> bool:
        return (self.used_bytes() + size) <= self.capacity_bytes

    def put_file_meta(self, path: str, size: int, kind: str = "blob", hash_: str = "") -> bool:
        if not self.can_store(size):
            return False
        self.files[path] = FileMeta(path=path, size=size, kind=kind, hash=hash_)
        self.flush()
        return True

    def seed_files(self) -> None:
        # Seed with small metadata (KB–MB)
        for i in range(random.randint(2, 10)):
            size = random.randint(5_000, 800_000)
            p = f"/seed/file_{i}.bin"
            self.files[p] = FileMeta(path=p, size=size)
        self.flush()

    def flush(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "capacity_bytes": self.capacity_bytes,
                    "used_bytes": self.used_bytes(),
                    "files": {k: vars(v) for k, v in self.files.items()},
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

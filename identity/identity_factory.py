from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from identity.names_provider import NameProvider


@dataclass
class Identity:
    display_name: str     # loglarda gözükecek isim
    username: str         # login denemelerinde kullanacağın isim
    hostname: str         # cihaz adı
    identity_type: str    # person | fake_person | bot | service | system


class IdentityFactory:
    """
    Kurallar:
    - Person: gerçek isim + kurumsal hostname
    - Attacker: fake_person (gerçek gibi), bot, veya service account
    - System: sunucu / cihaz tipi hostname
    """
    def __init__(self, seed: int, org_prefix: str = "GK") -> None:
        self.rng = random.Random(seed)
        self.names = NameProvider(seed)
        self.org = org_prefix

    # ---------- hostnames ----------
    def _hostname_client(self) -> str:
        return f"{self.org}-LT-{self.rng.randint(1000, 9999)}"

    def _hostname_branch_pc(self, branch_id: str) -> str:
        return f"{self.org}-{branch_id}-PC-{self.rng.randint(1, 80):02d}"

    def _hostname_warehouse_iot(self, wh_id: str) -> str:
        kind = self.rng.choice(["RF", "PRN", "CAM", "SENSOR"])
        return f"{self.org}-{wh_id}-{kind}-{self.rng.randint(1, 200):03d}"

    def _hostname_server(self, role: str) -> str:
        return f"{self.org}-SRV-{role.upper()}-{self.rng.randint(1, 9):02d}"

    # ---------- identities ----------
    def person(self, hostname: Optional[str] = None) -> Identity:
        full = self.names.full_name()
        user = self.names.username_from_name(full)
        host = hostname or self._hostname_client()
        return Identity(display_name=full, username=user, hostname=host, identity_type="person")

    def branch_user(self, branch_label: str) -> Identity:
        full = self.names.full_name()
        user = self.names.username_from_name(full)
        host = self._hostname_branch_pc(branch_label)
        return Identity(display_name=full, username=user, hostname=host, identity_type="person")

    def warehouse_device(self, wh_label: str) -> Identity:
        # warehouse IoT cihazlarında insan ismi olmaz
        host = self._hostname_warehouse_iot(wh_label)
        return Identity(display_name=host, username=host.lower(), hostname=host, identity_type="system")

    def system_server(self, role: str) -> Identity:
        host = self._hostname_server(role)
        return Identity(display_name=host, username=host.lower(), hostname=host, identity_type="system")

    def attacker(self) -> Identity:
        r = self.rng.random()
        if r < 0.45:
            # sahte gerçek isim (social engineering)
            full = self.names.full_name()
            user = self.names.username_from_name(full)
            host = f"UNKNOWN-{self.rng.randint(100,999)}"
            return Identity(display_name=full, username=user, hostname=host, identity_type="fake_person")
        elif r < 0.80:
            # bot / tool adı
            bot = self.names.bot_name()
            return Identity(display_name=bot, username=bot, hostname=bot.upper(), identity_type="bot")
        else:
            # service-like
            svc = self.names.service_account()
            host = f"{svc.upper()}-{self.rng.randint(1,99):02d}"
            return Identity(display_name=svc, username=svc, hostname=host, identity_type="service")

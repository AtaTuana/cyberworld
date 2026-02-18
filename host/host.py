from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from host.disk import VirtualDisk
from host.users import UserDB
from host.process import ProcessManager
from services.base import Service


@dataclass
class Host:
    host_id: str
    ip: str
    network_id: str
    role: str
    disk: VirtualDisk
    users: UserDB
    world_id: str

    services: Dict[str, Service] = field(default_factory=dict)
    procman: ProcessManager = field(default_factory=ProcessManager)

    def add_service(self, svc: Service) -> None:
        self.services[svc.name] = svc

    def has_service(self, name: str) -> bool:
        return name in self.services

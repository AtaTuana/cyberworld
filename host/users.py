from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass
class User:
    username: str
    password: str
    is_admin: bool = False


class UserDB:
    def __init__(self) -> None:
        self.users: Dict[str, User] = {}

    def add_user(self, username: str, password: str, is_admin: bool = False) -> None:
        self.users[username] = User(username=username, password=password, is_admin=is_admin)

    def check(self, username: str, password: str) -> bool:
        u = self.users.get(username)
        return bool(u and u.password == password)

from __future__ import annotations

import itertools

_session_counter = itertools.count(1)
_entity_counter = itertools.count(1)


def next_session_id(prefix: str = "sess_") -> str:
    return f"{prefix}{next(_session_counter)}"


def next_entity_id(prefix: str = "e") -> str:
    return f"{prefix}{next(_entity_counter)}"

from __future__ import annotations

import random
from typing import Sequence, TypeVar

T = TypeVar("T")


def weighted_choice(items: Sequence[T], weights: Sequence[float]) -> T:
    return random.choices(list(items), weights=list(weights), k=1)[0]


def rand_int(a: int, b: int) -> int:
    return random.randint(a, b)


def rand_float(a: float, b: float) -> float:
    return random.uniform(a, b)


def chance(p: float) -> bool:
    return random.random() < p


def pick(seq: Sequence[T]) -> T:
    return random.choice(list(seq))

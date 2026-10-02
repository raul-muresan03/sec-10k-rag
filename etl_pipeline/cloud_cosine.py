"""Cosine similarity without overflowing products of finite embedding values."""

from math import hypot
from collections.abc import Sequence


def cosine(first: Sequence[float], second: Sequence[float]) -> float:
    first_norm, second_norm = hypot(*first), hypot(*second)
    return sum((a / first_norm) * (b / second_norm) for a, b in zip(first, second, strict=True))

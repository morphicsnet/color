from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple, TypeVar, Callable

T = TypeVar("T")


def quantize(x: float, dp: int = 12) -> float:
    """
    Deterministic quantization: round-half-to-even at given decimal places.
    """
    return round(float(x), ndigits=dp)


def qtuple(vals: Sequence[float], dp: int = 12) -> Tuple[float, ...]:
    return tuple(quantize(v, dp) for v in vals)


def approx_equal(x: float, y: float, tol: float = 1e-9) -> bool:
    return abs(x - y) <= tol


def stable_sorted(items: Iterable[T], key: Callable[[T], object]) -> List[T]:
    # Python sort is stable; enforce deterministic order via key only
    return sorted(items, key=key)


def clamp_angle_pi(h: float) -> float:
    """
    Map angle to canonical interval [-pi, pi).
    """
    # Use math.remainder to wrap into (-pi, pi]; then adjust edge pi -> -pi
    wrapped = math.remainder(h, 2.0 * math.pi)  # in (-pi, pi]
    if approx_equal(wrapped, math.pi, 1e-15) or wrapped > math.pi:
        wrapped = -math.pi
    # ensure -pi <= wrapped < pi
    if wrapped < -math.pi:
        wrapped += 2.0 * math.pi
    if wrapped >= math.pi:
        wrapped -= 2.0 * math.pi
    return wrapped


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b != 0.0 else default
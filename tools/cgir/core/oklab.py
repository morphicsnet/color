from __future__ import annotations

import math
from typing import Tuple

from .numeric import quantize, qtuple, approx_equal, clamp_angle_pi


def to_lch(L: float, a: float, b: float, dp: int = 12) -> Tuple[float, float, float]:
    """
    Convert OKLab (L,a,b) to (L,h,S') with canonical hue wrapping to [-pi, pi).
    S' is the radial magnitude in the ab-plane.
    """
    Sprime = math.hypot(a, b)  # sqrt(a^2 + b^2)
    if Sprime == 0.0:
        # Hue undefined on gray axis; choose canonical h = 0
        h = 0.0
    else:
        h = math.atan2(b, a)
        h = clamp_angle_pi(h)
    Lq, hq, Sq = quantize(L, dp), quantize(h, dp), quantize(Sprime, dp)
    return (Lq, hq, Sq)


def from_lch(L: float, h: float, Sprime: float, dp: int = 12) -> Tuple[float, float, float]:
    """
    Convert (L,h,S') to OKLab (L,a,b) using a = S' cos h, b = S' sin h with canonical hue wrapping.
    """
    h = clamp_angle_pi(h)
    a = Sprime * math.cos(h)
    b = Sprime * math.sin(h)
    return qtuple((L, a, b), dp)


def gray_axis_bias(L: float, a: float, b: float, tol: float = 1e-12, dp: int = 12) -> Tuple[float, float, float]:
    """
    Canonicalization near the gray axis:
      - If |a| and |b| are below tol, snap to exactly a=b=0 and canonicalize hue to 0 under to_lch().
    """
    if abs(a) <= tol and abs(b) <= tol:
        return (quantize(L, dp), 0.0, 0.0)
    return qtuple((L, a, b), dp)


def mix_oklab_convex(
    L1: float, a1: float, b1: float,
    L2: float, a2: float, b2: float,
    w1: float, w2: float,
    dp: int = 12
) -> Tuple[float, float, float]:
    """
    Two-point convex mix in OKLab, with weights w1, w2 (nonnegative). Normalizes if sum != 1.
    Provided for convenience; the general n-ary mixing is typically done elsewhere.
    """
    s = w1 + w2
    if s <= 0.0:
        # default to first
        return qtuple((L1, a1, b1), dp)
    w1n = w1 / s
    w2n = w2 / s
    L = w1n * L1 + w2n * L2
    a = w1n * a1 + w2n * a2
    b = w1n * b1 + w2n * b2
    return qtuple((L, a, b), dp)
from __future__ import annotations

import math
from typing import Tuple

from .numeric import quantize, qtuple, approx_equal
from .oklab import to_lch, from_lch, gray_axis_bias


def cmax_ok_v1(L: float, h: float) -> float:
    """
    Heuristic Cmax(L,h) for OKLab droplet boundary (v1 placeholder).
    Notes:
      - This is NOT a colorimetrically accurate gamut boundary; it provides a
        smooth L- and h-dependent bound for deterministic projection in MVP.
      - At mid-L (L=0.5), allow higher chroma; taper toward L=0 or L=1.
      - Small hue modulation to avoid degeneracy and test invariance.
    Returns:
      max allowable S' (radial ab-plane magnitude) for given L,h.
    """
    # Base envelope: tent shape over L \in [0,1]
    base = 0.35 * (1.0 - abs(2.0 * L - 1.0)) + 0.05  # in [0.05, 0.40]
    # Hue modulation: gentle sinusoidal ripple
    ripple = 0.03 * math.sin(3.0 * h)  # [-0.03, 0.03]
    # Ensure nonnegative
    return max(0.0, base + ripple)


def project_radial_clamp(
    L: float, a: float, b: float, tol: float = 1e-12, dp: int = 12
) -> Tuple[float, float, float]:
    """
    Radial clamp projection into the OKLab droplet:
      1) Convert (L,a,b) -> (L,h,S')
      2) Clamp S' to min(S', Cmax(L,h))
      3) Convert back to (L,a,b), apply gray_axis_bias canonicalization
      4) Quantize to dp decimals (half-to-even)
    """
    L0, h0, Sprime0 = to_lch(L, a, b, dp=dp)
    Smax = cmax_ok_v1(L0, h0)
    Sprime = min(Sprime0, Smax)
    Lp, ap, bp = from_lch(L0, h0, Sprime, dp=dp)
    Lc, ac, bc = gray_axis_bias(Lp, ap, bp, tol=tol, dp=dp)
    return qtuple((Lc, ac, bc), dp=dp)


def is_inside_droplet(L: float, a: float, b: float, tol: float = 1e-12, dp: int = 12) -> bool:
    """
    Check if (L,a,b) lies inside the droplet: i.e., S' <= Cmax(L,h) up to tolerance.
    """
    L0, h0, Sprime0 = to_lch(L, a, b, dp=dp)
    Smax = cmax_ok_v1(L0, h0)
    return Sprime0 <= Smax + tol


def clamp_to_droplet_and_test(
    L: float, a: float, b: float, tol: float = 1e-12, dp: int = 12
) -> Tuple[Tuple[float, float, float], bool]:
    """
    Convenience: returns (projected_oklab, inside_before_projection)
    """
    inside = is_inside_droplet(L, a, b, tol=tol, dp=dp)
    projected = project_radial_clamp(L, a, b, tol=tol, dp=dp)
    return projected, inside
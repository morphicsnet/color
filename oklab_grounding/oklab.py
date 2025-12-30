"""
OKLab space implementation for the grounding framework.
"""

from typing import List, Tuple
import math
from .space import GroundSpace, Symbol
from .numeric import quantize, qtuple, clamp_angle_pi

# OKLab color type
class OKLab:
    def __init__(self, L: float, a: float, b: float):
        self.L = L
        self.a = a
        self.b = b

    def __repr__(self):
        return f"OKLab(L={self.L}, a={self.a}, b={self.b})"

    def __eq__(self, other):
        if not isinstance(other, OKLab):
            return False
        return (self.L == other.L and
                self.a == other.a and
                self.b == other.b)

    def __iter__(self):
        yield self.L
        yield self.a
        yield self.b

class OKLabSpace(GroundSpace[OKLab]):
    """
    OKLab color space implementation of GroundSpace.

    Provides perceptual distance, color mixing, and validation for OKLab colors.
    """

    def distance(self, a: OKLab, b: OKLab) -> float:
        """Perceptual distance in OKLab space."""
        dl = a.L - b.L
        da = a.a - b.a
        db = a.b - b.b
        return math.sqrt(dl*dl + da*da + db*db)

    def mix(self, points: List[OKLab], weights: List[float]) -> OKLab:
        """Convex combination of OKLab colors."""
        if not points:
            raise ValueError("Cannot mix empty list of points")
        if len(points) != len(weights):
            raise ValueError("Points and weights must have same length")

        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            # Equal weights if all zero
            normalized_weights = [1.0 / len(points)] * len(points)
        else:
            normalized_weights = [w / total_weight for w in weights]

        # Mix in OKLab space
        mixed_L = sum(p.L * w for p, w in zip(points, normalized_weights))
        mixed_a = sum(p.a * w for p, w in zip(points, normalized_weights))
        mixed_b = sum(p.b * w for p, w in zip(points, normalized_weights))

        return OKLab(mixed_L, mixed_a, mixed_b)

    def validate(self, point: OKLab) -> bool:
        """Check if OKLab color is valid (within reasonable bounds)."""
        # OKLab has L in [0,1], a,b typically in [-0.5, 0.5] but can be wider
        return (0 <= point.L <= 1 and
                -1 <= point.a <= 1 and
                -1 <= point.b <= 1)

# Predefined color regions for common symbols
class SphericalRegion:
    """Simple spherical region around a center point."""

    def __init__(self, center: OKLab, radius: float, space: OKLabSpace):
        self.center = center
        self.radius = radius
        self.space = space

    def contains(self, point: OKLab) -> bool:
        return self.space.distance(self.center, point) <= self.radius

# Utility functions for creating common color regions
def create_color_region(color_name: str, space: OKLabSpace) -> 'SphericalRegion':
    """Create a region for a named color."""
    # Simplified color mapping - in practice would use OKLab values for actual colors
    color_map = {
        "red": OKLab(0.5, 0.3, 0.2),
        "blue": OKLab(0.4, -0.1, -0.3),
        "green": OKLab(0.6, -0.2, 0.2),
        "yellow": OKLab(0.8, 0.1, 0.2),
        "purple": OKLab(0.4, 0.1, -0.2)
    }

    center = color_map.get(color_name.lower(), OKLab(0.5, 0, 0))
    return SphericalRegion(center, 0.1, space)  # Small radius for distinct regions
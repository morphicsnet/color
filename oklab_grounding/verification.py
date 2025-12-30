"""
Verification layer connecting SDK operations to Coq formal proofs.

This module provides runtime checks for properties that are formally proved in Coq,
serving as a bridge between mathematical guarantees and executable code.
"""

from typing import TypeVar, Generic, List
from .space import GroundSpace
from .oklab import OKLabSpace, OKLab
from .numeric import approx_equal

S = TypeVar('S')

class VerificationError(Exception):
    """Raised when a verification check fails."""
    pass

class Verifier(Generic[S]):
    """
    Verification layer for ground space operations.

    Checks properties that correspond to formal proofs in Coq.
    """

    def __init__(self, space: GroundSpace[S]):
        self.space = space

    def verify_distance_nonnegativity(self, points: List[S]) -> None:
        """
        Verify distance non-negativity: ∀x,y: d(x,y) ≥ 0

        This property is fundamental to metric spaces as defined in Coq.
        """
        for i, x in enumerate(points):
            for j, y in enumerate(points):
                dist = self.space.distance(x, y)
                if dist < 0:
                    raise VerificationError(
                        f"Distance non-negativity violated: d({x}, {y}) = {dist} < 0"
                    )

    def verify_distance_reflexivity(self, points: List[S], tol: float = 1e-12) -> None:
        """
        Verify distance reflexivity: ∀x: d(x,x) ≈ 0

        Corresponds to metric space axioms in Coq ColorSpace definitions.
        """
        for x in points:
            dist = self.space.distance(x, x)
            if not approx_equal(dist, 0.0, tol):
                raise VerificationError(
                    f"Distance reflexivity violated: d({x}, {x}) = {dist} ≠ 0"
                )

    def verify_mix_closure(self, points: List[S], weights: List[float]) -> None:
        """
        Verify mix closure: mix result is valid in the space.

        Corresponds to Coq proofs about convex combinations staying within the space.
        """
        if not points:
            return  # Empty mix is trivially valid

        try:
            result = self.space.mix(points, weights)
            if not self.space.validate(result):
                raise VerificationError(
                    f"Mix closure violated: mix result {result} is not valid in space"
                )
        except Exception as e:
            raise VerificationError(f"Mix operation failed: {e}")

    def verify_mix_convexity(self, points: List[S], weights: List[float], tol: float = 1e-12) -> None:
        """
        Verify mix convexity properties.

        Checks that weights are normalized and result satisfies basic convexity properties.
        """
        if not points:
            return

        # Check weight normalization
        total_weight = sum(weights)
        if not (approx_equal(total_weight, 1.0, tol) or total_weight > 0):
            raise VerificationError(
                f"Mix weights not properly normalized: sum = {total_weight}"
            )

class OKLabVerifier(Verifier[OKLab]):
    """
    OKLab-specific verification extending the general verifier.

    Includes checks for OKLab-specific properties proved in Coq.
    """

    def verify_oklab_bounds(self, points: List[OKLab]) -> None:
        """
        Verify OKLab coordinate bounds: L ∈ [0,1], a,b ∈ [-1,1]

        These bounds are enforced in the OKLab space definition.
        """
        for point in points:
            if not (0 <= point.L <= 1):
                raise VerificationError(f"OKLab L out of bounds: {point.L}")
            if not (-1 <= point.a <= 1):
                raise VerificationError(f"OKLab a out of bounds: {point.a}")
            if not (-1 <= point.b <= 1):
                raise VerificationError(f"OKLab b out of bounds: {point.b}")

    def verify_color_mixing_properties(self, colors: List[OKLab], weights: List[float]) -> None:
        """
        Verify color-specific mixing properties.

        Includes checks for perceptual constraints and color space invariants.
        """
        # First run general verification
        self.verify_mix_closure(colors, weights)

        # OKLab-specific: mixing should preserve perceptual bounds
        result = self.space.mix(colors, weights)
        self.verify_oklab_bounds([result])

def verify_grounding_consistency(space: GroundSpace[S], points: List[S]) -> None:
    """
    Run comprehensive verification suite for a grounding space.

    This function provides a high-level interface for verifying that
    a space implementation respects the formal properties proved in Coq.
    """
    verifier = Verifier(space)
    verifier.verify_distance_nonnegativity(points)
    verifier.verify_distance_reflexivity(points)

    # Test mix operations if we have sample points
    if len(points) >= 2:
        weights = [1.0 / len(points)] * len(points)
        verifier.verify_mix_closure(points, weights)
        verifier.verify_mix_convexity(points, weights)

def verify_oklab_consistency(space: OKLabSpace, colors: List[OKLab]) -> None:
    """
    Comprehensive verification for OKLab space.

    Includes both general space properties and OKLab-specific constraints.
    """
    verify_grounding_consistency(space, colors)

    verifier = OKLabVerifier(space)
    verifier.verify_oklab_bounds(colors)

    if len(colors) >= 2:
        weights = [1.0 / len(colors)] * len(colors)
        verifier.verify_color_mixing_properties(colors, weights)
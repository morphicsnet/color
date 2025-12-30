"""
Tests for verification layer.
"""

import pytest
from oklab_grounding.oklab import OKLabSpace, OKLab
from oklab_grounding.verification import Verifier, OKLabVerifier, verify_oklab_consistency


class TestVerifier:
    def test_distance_properties(self):
        space = OKLabSpace()
        verifier = Verifier(space)

        colors = [
            OKLab(L=0.5, a=0.1, b=0.2),
            OKLab(L=0.6, a=-0.1, b=0.1),
            OKLab(L=0.4, a=0.2, b=-0.1)
        ]

        # Should not raise exceptions
        verifier.verify_distance_nonnegativity(colors)
        verifier.verify_distance_reflexivity(colors)

    def test_mix_properties(self):
        space = OKLabSpace()
        verifier = Verifier(space)

        colors = [
            OKLab(L=0.5, a=0.1, b=0.2),
            OKLab(L=0.6, a=-0.1, b=0.1)
        ]
        weights = [0.6, 0.4]

        # Should not raise exceptions
        verifier.verify_mix_closure(colors, weights)
        verifier.verify_mix_convexity(colors, weights)


class TestOKLabVerifier:
    def test_bounds_checking(self):
        space = OKLabSpace()
        verifier = OKLabVerifier(space)

        valid_colors = [
            OKLab(L=0.5, a=0.1, b=0.2),
            OKLab(L=0.0, a=0.0, b=0.0),  # Boundary valid
            OKLab(L=1.0, a=0.0, b=0.0)   # Boundary valid
        ]

        verifier.verify_oklab_bounds(valid_colors)

    def test_invalid_bounds_raise_error(self):
        space = OKLabSpace()
        verifier = OKLabVerifier(space)

        invalid_colors = [
            OKLab(L=1.5, a=0.1, b=0.2),  # L > 1
            OKLab(L=0.5, a=1.5, b=0.2),  # a > 1
        ]

        with pytest.raises(Exception):  # VerificationError
            verifier.verify_oklab_bounds(invalid_colors)

    def test_mixing_properties(self):
        space = OKLabSpace()
        verifier = OKLabVerifier(space)

        colors = [
            OKLab(L=0.5, a=0.1, b=0.2),
            OKLab(L=0.6, a=-0.1, b=0.1)
        ]
        weights = [0.7, 0.3]

        # Should not raise exceptions
        verifier.verify_color_mixing_properties(colors, weights)


class TestVerificationAPI:
    def test_verify_oklab_consistency_success(self):
        space = OKLabSpace()
        colors = [
            OKLab(L=0.5, a=0.1, b=0.2),
            OKLab(L=0.6, a=-0.1, b=0.1),
            OKLab(L=0.4, a=0.0, b=0.0)
        ]

        # Should not raise exceptions
        verify_oklab_consistency(space, colors)

    def test_verify_oklab_consistency_failure(self):
        space = OKLabSpace()
        colors = [
            OKLab(L=1.5, a=0.1, b=0.2),  # Invalid lightness
        ]

        with pytest.raises(Exception):
            verify_oklab_consistency(space, colors)
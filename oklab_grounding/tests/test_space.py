"""
Tests for grounding space abstractions.
"""

import pytest
from oklab_grounding.space import GroundSpace, Grounding, Symbol
from oklab_grounding.oklab import OKLabSpace, OKLab, SphericalRegion


class TestOKLabSpace:
    def test_distance_reflexive(self):
        space = OKLabSpace()
        color = OKLab(L=0.5, a=0.1, b=0.2)
        assert space.distance(color, color) == pytest.approx(0.0, abs=1e-10)

    def test_distance_symmetric(self):
        space = OKLabSpace()
        c1 = OKLab(L=0.5, a=0.1, b=0.2)
        c2 = OKLab(L=0.6, a=-0.1, b=0.1)
        assert space.distance(c1, c2) == space.distance(c2, c1)

    def test_distance_non_negative(self):
        space = OKLabSpace()
        colors = [
            OKLab(L=0.5, a=0.1, b=0.2),
            OKLab(L=0.6, a=-0.1, b=0.1),
            OKLab(L=0.7, a=0.05, b=-0.05)
        ]
        for c1 in colors:
            for c2 in colors:
                assert space.distance(c1, c2) >= 0

    def test_mix_single_color(self):
        space = OKLabSpace()
        color = OKLab(L=0.5, a=0.1, b=0.2)
        result = space.mix([color], [1.0])
        assert result.L == pytest.approx(color.L)
        assert result.a == pytest.approx(color.a)
        assert result.b == pytest.approx(color.b)

    def test_mix_equal_weights(self):
        space = OKLabSpace()
        c1 = OKLab(L=0.4, a=0.0, b=0.0)
        c2 = OKLab(L=0.6, a=0.0, b=0.0)
        result = space.mix([c1, c2], [0.5, 0.5])
        assert result.L == pytest.approx(0.5)
        assert result.a == pytest.approx(0.0)
        assert result.b == pytest.approx(0.0)

    def test_validate_valid_color(self):
        space = OKLabSpace()
        color = OKLab(L=0.5, a=0.1, b=0.2)
        assert space.validate(color)

    def test_validate_invalid_lightness(self):
        space = OKLabSpace()
        color = OKLab(L=1.5, a=0.1, b=0.2)  # L > 1
        assert not space.validate(color)


class TestGrounding:
    def test_bind_and_get_region(self):
        space = OKLabSpace()
        grounding = Grounding(space)

        region = SphericalRegion(OKLab(L=0.5, a=0.1, b=0.2), 0.1, space)
        grounding.bind_region("test_color", region)

        retrieved = grounding.get_region("test_color")
        assert retrieved is region

    def test_get_nonexistent_region_raises(self):
        space = OKLabSpace()
        grounding = Grounding(space)

        with pytest.raises(ValueError, match="No region bound"):
            grounding.get_region("nonexistent")

    def test_nearest_symbol_direct_hit(self):
        space = OKLabSpace()
        grounding = Grounding(space)

        center = OKLab(L=0.5, a=0.1, b=0.2)
        region = SphericalRegion(center, 0.1, space)
        grounding.bind_region("target", region)

        # Point inside region should return the symbol
        result = grounding.nearest_symbol(center)
        assert result == "target"

    def test_similarity_different_colors(self):
        space = OKLabSpace()
        grounding = Grounding(space)

        c1 = OKLab(L=0.5, a=0.1, b=0.2)
        c2 = OKLab(L=0.6, a=-0.1, b=0.1)
        r1 = SphericalRegion(c1, 0.1, space)
        r2 = SphericalRegion(c2, 0.1, space)

        grounding.bind_region("color1", r1)
        grounding.bind_region("color2", r2)

        similarity = grounding.similarity("color1", "color2")
        assert 0 < similarity < 1  # Should be positive but less than 1

    def test_similarity_same_color(self):
        space = OKLabSpace()
        grounding = Grounding(space)

        color = OKLab(L=0.5, a=0.1, b=0.2)
        region = SphericalRegion(color, 0.1, space)
        grounding.bind_region("color", region)

        similarity = grounding.similarity("color", "color")
        assert similarity == pytest.approx(1.0, abs=1e-10)
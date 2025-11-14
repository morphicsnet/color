"""
cgir.core subpackage
Numeric policy, OKLab/OKLch conversions, droplet projection, and mixing utilities.
"""

from .numeric import quantize, qtuple, approx_equal, clamp_angle_pi  # re-export
from .oklab import to_lch, from_lch, gray_axis_bias
from .droplet import cmax_ok_v1, project_radial_clamp, is_inside_droplet, clamp_to_droplet_and_test

__all__ = [
    "quantize",
    "qtuple",
    "approx_equal",
    "clamp_angle_pi",
    "to_lch",
    "from_lch",
    "gray_axis_bias",
    "cmax_ok_v1",
    "project_radial_clamp",
    "is_inside_droplet",
    "clamp_to_droplet_and_test",
]
"""
OKLab Grounding Framework

A framework for symbol grounding over perceptual spaces, instantiated in OKLab color geometry.
"""

from .space import GroundSpace, GroundRegion, Grounding, Symbol
from .oklab import OKLabSpace, SphericalRegion
from .cgir import CGIRBuilder, SpaceDefinition, StateVariable, Interaction, Operator, GeometricIntent
from .verification import Verifier, OKLabVerifier, verify_grounding_consistency, verify_oklab_consistency
from .server import run_server

__all__ = [
    'GroundSpace',
    'GroundRegion',
    'Grounding',
    'Symbol',
    'OKLabSpace',
    'SphericalRegion',
    'CGIRBuilder',
    'SpaceDefinition',
    'StateVariable',
    'Interaction',
    'Operator',
    'GeometricIntent',
    'Verifier',
    'OKLabVerifier',
    'verify_grounding_consistency',
    'verify_oklab_consistency',
    'run_server'
]
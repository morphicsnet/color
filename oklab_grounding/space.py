"""
Core abstractions for symbol grounding framework.

Extracted from Coq formal specifications in coq/Color/Core.v
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Dict, List, Protocol
import math

# Type variable for points in the space
S = TypeVar('S')

# Symbol as string identifier (matching Coq Symbol := string)
Symbol = str

class GroundSpace(ABC, Generic[S]):
    """
    Abstract ground space for symbol grounding.

    Corresponds to Coq Record GroundSpace with carrier, distance, mix, validate.
    """

    @abstractmethod
    def distance(self, a: S, b: S) -> float:
        """Distance metric between points in the space."""
        pass

    @abstractmethod
    def mix(self, points: List[S], weights: List[float]) -> S:
        """Convex combination of points with weights."""
        pass

    @abstractmethod
    def validate(self, point: S) -> bool:
        """Check if point is valid in this space."""
        pass

class GroundRegion(ABC, Generic[S]):
    """
    Abstract geometric region in a ground space.

    Corresponds to Coq Record GroundRegion with contains predicate.
    """

    @abstractmethod
    def contains(self, point: S) -> bool:
        """Check if point is contained in this region."""
        pass

class Grounding(Generic[S]):
    """
    Mapping from symbols to regions in a ground space.

    Corresponds to Coq Record Grounding with regions function.
    """

    def __init__(self, space: GroundSpace[S]):
        self.space = space
        self._regions: Dict[Symbol, GroundRegion[S]] = {}

    def bind_region(self, symbol: Symbol, region: GroundRegion[S]) -> None:
        """Bind a symbol to a region in the space."""
        self._regions[symbol] = region

    def get_region(self, symbol: Symbol) -> GroundRegion[S]:
        """Get the region for a symbol."""
        return self._regions[symbol]

    def nearest_symbol(self, point: S) -> Symbol:
        """Find the symbol whose region is closest to the point."""
        if not self._regions:
            raise ValueError("No regions bound")

        min_distance = float('inf')
        nearest = None

        for symbol, region in self._regions.items():
            # Simple center-based distance for now
            # In practice, would need region-specific distance calculation
            if region.contains(point):
                return symbol
            # Placeholder: assume regions have a center method
            # This needs to be extended based on concrete region types
            try:
                center = getattr(region, 'center', lambda: point)()
                dist = self.space.distance(point, center)
                if dist < min_distance:
                    min_distance = dist
                    nearest = symbol
            except AttributeError:
                continue

        return nearest or list(self._regions.keys())[0]

    def similarity(self, symbol1: Symbol, symbol2: Symbol) -> float:
        """Calculate similarity between two symbols' regions."""
        region1 = self.get_region(symbol1)
        region2 = self.get_region(symbol2)

        # Placeholder implementation
        # In practice, would compute region overlap or distance
        try:
            center1 = getattr(region1, 'center', lambda: None)()
            center2 = getattr(region2, 'center', lambda: None)()
            if center1 is not None and center2 is not None:
                return 1.0 / (1.0 + self.space.distance(center1, center2))
        except AttributeError:
            pass

        return 0.0  # No similarity information available
# OKLab Grounding Framework API Documentation

## Core Abstractions

### GroundSpace

Abstract base class defining a perceptual space for symbol grounding.

#### Methods

##### `distance(a: S, b: S) -> float`
Calculates the perceptual distance between two points in the space.

**Parameters:**
- `a`, `b`: Points in the space

**Returns:** Distance value (non-negative)

##### `mix(points: List[S], weights: List[float]) -> S`
Performs convex combination of points with given weights.

**Parameters:**
- `points`: List of points to mix
- `weights`: Normalized weights (automatically normalized if sum ≠ 1)

**Returns:** Mixed point in the space

##### `validate(point: S) -> bool`
Checks if a point is valid within the space constraints.

**Parameters:**
- `point`: Point to validate

**Returns:** True if valid, False otherwise

### GroundRegion

Abstract base class defining geometric regions in ground spaces.

#### Methods

##### `contains(point: S) -> bool`
Tests if a point lies within the region.

**Parameters:**
- `point`: Point to test

**Returns:** True if point is contained in region

### Grounding

Main class for symbol-to-region mapping and grounding operations.

#### Constructor

##### `__init__(self, space: GroundSpace[S])`
Creates a new grounding instance for the given space.

**Parameters:**
- `space`: The ground space to use for operations

#### Methods

##### `bind_region(self, symbol: Symbol, region: GroundRegion[S]) -> None`
Associates a symbol with a geometric region.

**Parameters:**
- `symbol`: String identifier for the concept
- `region`: Geometric region defining the concept's extent

##### `get_region(self, symbol: Symbol) -> GroundRegion[S]`
Retrieves the region associated with a symbol.

**Parameters:**
- `symbol`: Symbol to look up

**Returns:** Associated region

**Raises:** ValueError if symbol not found

##### `nearest_symbol(self, point: S) -> Symbol | None`
Finds the symbol whose region contains the given point, or the closest region.

**Parameters:**
- `point`: Query point in the space

**Returns:** Nearest symbol or None if no regions defined

##### `similarity(self, symbol1: Symbol, symbol2: Symbol) -> float`
Calculates similarity between two symbols based on region overlap/distance.

**Parameters:**
- `symbol1`, `symbol2`: Symbols to compare

**Returns:** Similarity score between 0.0 and 1.0

## OKLab Implementation

### OKLabSpace

Concrete implementation of GroundSpace for OKLab color space.

#### Methods

All GroundSpace methods are implemented with OKLab-specific logic:

- **Distance**: Euclidean distance in OKLab coordinate space
- **Mixing**: Convex combination in OKLab (perceptually uniform)
- **Validation**: OKLab bounds checking (L ∈ [0,1], a,b ∈ [-1,1])

### OKLab

Data class representing a color in OKLab space.

#### Attributes
- `L: float` - Lightness component (0.0 to 1.0)
- `a: float` - Green-red axis (-1.0 to 1.0)
- `b: float` - Blue-yellow axis (-1.0 to 1.0)

### SphericalRegion

Circular/spherical regions defined by center and radius.

#### Constructor

##### `__init__(self, center: OKLab, radius: float, space: OKLabSpace)`
Creates a spherical region.

**Parameters:**
- `center`: Center point of the region
- `radius`: Radius defining region extent
- `space`: Associated space for distance calculations

## Geometric IR (CGIR)

### CGIRBuilder

Builder class for constructing Color Geometry Intermediate Representations.

#### Constructor

##### `__init__(self, version: str = "0.1.0")`
Creates a new CGIR builder.

**Parameters:**
- `version`: CGIR format version

#### Methods

##### `add_space(self, space: SpaceDefinition) -> CGIRBuilder`
Adds a geometric manifold definition.

##### `add_state_variable(self, var: StateVariable) -> CGIRBuilder`
Adds a state variable living on a manifold.

##### `add_interaction(self, interaction: Interaction) -> CGIRBuilder`
Adds an energy term or coupling between variables.

##### `add_operator(self, operator: Operator) -> CGIRBuilder`
Adds a canonical geometric operator.

##### `add_intent(self, intent: GeometricIntent) -> CGIRBuilder`
Adds a geometric intent for operations.

##### `simulate(self, steps: int = 100, dt: float = 0.01) -> List[Dict]`
Runs geometric simulation over time steps.

**Returns:** Trajectory of state snapshots

##### `to_dict(self) -> Dict`
Converts to dictionary representation.

##### `to_json(self, indent: int = 2) -> str`
Converts to JSON string.

## Verification Layer

### Verifier

Base class for runtime verification of space properties.

#### Methods

##### `verify_distance_nonnegativity(self, points: List[S]) -> None`
Ensures distance is always non-negative.

##### `verify_distance_reflexivity(self, points: List[S], tol: float = 1e-12) -> None`
Ensures d(x,x) ≈ 0 for all points.

##### `verify_mix_closure(self, points: List[S], weights: List[float]) -> None`
Ensures mixing results remain valid in the space.

##### `verify_mix_convexity(self, points: List[S], weights: List[float], tol: float = 1e-12)`
Ensures proper weight normalization.

### OKLabVerifier

OKLab-specific verification extending the base verifier.

#### Methods

##### `verify_oklab_bounds(self, colors: List[OKLab]) -> None`
Validates OKLab coordinate bounds.

##### `verify_color_mixing_properties(self, colors: List[OKLab], weights: List[float]) -> None`
Validates color-specific mixing constraints.

## Utility Functions

### verify_grounding_consistency(space: GroundSpace[S], points: List[S]) -> None
Comprehensive verification of space properties.

### verify_oklab_consistency(space: OKLabSpace, colors: List[OKLab]) -> None
OKLab-specific consistency verification.

## HTTP API

### Endpoints

#### `GET /health`
Health check endpoint.

**Returns:**
```json
{
  "status": "ok",
  "service": "oklab-grounding-server"
}
```

#### `POST /spaces/oklab`
Create a new OKLab space instance.

**Request:**
```json
{
  "id": "my_space"
}
```

#### `POST /groundings/{grounding_id}/bind`
Bind a symbol to a region.

**Request:**
```json
{
  "symbol": "danger",
  "region": {
    "center": {"L": 0.5, "a": 0.3, "b": 0.2},
    "radius": 0.1
  }
}
```

#### `POST /groundings/{grounding_id}/query/nearest`
Find nearest symbol to a point.

**Request:**
```json
{
  "point": {"L": 0.48, "a": 0.28, "b": 0.18}
}
```

**Response:**
```json
{
  "nearest_symbol": "danger"
}
```

#### `POST /spaces/oklab/mix`
Mix colors with given weights.

**Request:**
```json
{
  "colors": [
    {"L": 0.5, "a": 0.3, "b": 0.2},
    {"L": 0.6, "a": -0.2, "b": 0.2}
  ],
  "weights": [0.6, 0.4]
}
```

**Response:**
```json
{
  "result": {"L": 0.54, "a": 0.12, "b": 0.2}
}
```

#### `POST /cgir/simulate`
Run CGIR simulation.

**Request:**
```json
{
  "cgir": {...},
  "steps": 100
}
```

**Response:**
```json
{
  "trajectory": [
    {"step": 0, "time": 0.0, "state": {...}},
    {"step": 1, "time": 0.01, "state": {...}},
    ...
  ]
}
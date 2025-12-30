# OKLab Grounding Framework Architecture

This document provides a comprehensive overview of the OKLab Grounding Framework's architecture, design principles, and component interactions.

## Overview

The OKLab Grounding Framework implements a **layered architecture** for symbol grounding over perceptual spaces. It transforms discrete symbols into continuous perceptual representations, enabling applications that bridge symbolic AI with perceptual computing.

## Core Design Principles

### 1. Formal Foundations
- **Coq Integration**: Core abstractions are formally specified and proved in Coq
- **Mathematical Guarantees**: Runtime verification ensures operations respect formal properties
- **Constructive Mathematics**: All proofs are constructive, enabling code extraction

### 2. Perceptual Accuracy
- **Uniform Color Space**: OKLab provides perceptually uniform distance metrics
- **Geometric Operations**: Mixing and transformations preserve perceptual relationships
- **Validation**: Continuous validation against perceptual constraints

### 3. Multi-Language Support
- **Consistent Semantics**: Identical behavior across Python and TypeScript implementations
- **Language Idioms**: Each SDK follows target language conventions
- **Cross-Language Interop**: HTTP APIs enable seamless integration

### 4. Extensible Design
- **Geometric IR**: Generalized intermediate representation supports arbitrary manifolds
- **Plugin Architecture**: New spaces and operations can be added without core changes
- **Backward Compatibility**: Legacy CGIR workflows continue to function

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                       │
│  UI Design Systems • Neurosymbolic AI • Research Tools     │
└─────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────┐
│                    LANGUAGE SDKs                            │
│  Python (oklab_grounding) • TypeScript (@oklab/grounding)  │
└─────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────┐
│                    GEOMETRIC IR                             │
│  Spaces • State Variables • Interactions • Intents         │
└─────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────┐
│                   CORE RUNTIME                              │
│  GroundSpace • GroundRegion • Grounding • Verification     │
└─────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────┐
│                   FORMAL SPECIFICATION                      │
│  Coq Proofs • Mathematical Definitions • Property Proofs   │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Formal Specification Layer (Coq)

#### ColorCore.v
```coq
Module ColorCore.

(* A simple alias for the XYZ coordinate triple over R *)
Definition R3 := (R * R * R)%type.

(* Morphisms between coordinate spaces *)
Record Transform (A B : Type) := {
  run : A -> B
}.

(* Metrics over a space *)
Record Metric (X : Type) := {
  dist : X -> X -> R
}.

(* Grounding abstractions *)
Definition Symbol := string.

Record GroundSpace := {
  carrier  : Type;
  distance : carrier -> carrier -> R;
  mix      : list carrier -> list R -> carrier;
  validate : carrier -> bool
}.

Record GroundRegion (S : GroundSpace) := {
  contains : carrier S -> bool
}.

Record Grounding (S : GroundSpace) := {
  regions : Symbol -> GroundRegion S
}.

End ColorCore.
```

**Purpose**: Provides mathematical foundations with formal proofs
**Key Properties**:
- Distance non-negativity and reflexivity
- Transform composition associativity
- Mixing operation closure and convexity

### Core Runtime Layer

#### Abstract Interfaces
```python
class GroundSpace(ABC, Generic[S]):
    @abstractmethod
    def distance(self, a: S, b: S) -> float: ...

    @abstractmethod
    def mix(self, points: List[S], weights: List[float]) -> S: ...

    @abstractmethod
    def validate(self, point: S) -> bool: ...

class GroundRegion(ABC, Generic[S]):
    @abstractmethod
    def contains(self, point: S) -> bool: ...

class Grounding(Generic[S]):
    def bind_region(self, symbol: Symbol, region: GroundRegion[S]): ...
    def nearest_symbol(self, point: S) -> Symbol | None: ...
    def similarity(self, symbol1: Symbol, symbol2: Symbol) -> float: ...
```

**Purpose**: Language-agnostic abstractions extracted from Coq
**Key Features**:
- Generic type system supporting different spaces
- Consistent API across implementations
- Runtime property validation

#### OKLab Implementation
```python
class OKLabSpace(GroundSpace[OKLab]):
    def distance(self, a: OKLab, b: OKLab) -> float:
        # Euclidean distance in OKLab coordinates
        dl, da, db = a.L - b.L, a.a - b.a, a.b - b.b
        return math.sqrt(dl*dl + da*da + db*db)

    def mix(self, points: List[OKLab], weights: List[float]) -> OKLab:
        # Convex combination preserving perceptual uniformity
        total_weight = sum(weights)
        normalized = [w/total_weight for w in weights] if total_weight > 0 else weights

        mixed_L = sum(p.L * w for p, w in zip(points, normalized))
        mixed_a = sum(p.a * w for p, w in zip(points, normalized))
        mixed_b = sum(p.b * w for p, w in zip(points, normalized))

        return OKLab(mixed_L, mixed_a, mixed_b)

    def validate(self, point: OKLab) -> bool:
        # OKLab coordinate bounds validation
        return (0 <= point.L <= 1 and
                -1 <= point.a <= 1 and
                -1 <= point.b <= 1)
```

**Purpose**: Concrete perceptual space implementation
**Key Features**:
- Perceptually uniform color space
- Proper boundary validation
- Efficient geometric operations

### Geometric IR Layer

#### CGIR Schema Evolution
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Generalized Color Geometry IR",

  "properties": {
    "cgir_version": { "type": "string" },

    "spaces": {
      "type": "array",
      "items": {
        "properties": {
          "id": { "$ref": "#/$defs/ID" },
          "kind": { "enum": ["riemannian", "discrete", "statistical"] },
          "dim": { "type": "integer" },
          "coords": { "type": "string" },
          "metric": { "type": "string" }
        }
      }
    },

    "state": {
      "type": "array",
      "items": {
        "properties": {
          "id": { "$ref": "#/$defs/ID" },
          "space": { "$ref": "#/$defs/ID" },
          "kind": { "enum": ["point", "vector", "field", "neuron"] },
          "value": { "description": "Current state value" }
        }
      }
    },

    "interactions": {
      "type": "array",
      "items": {
        "properties": {
          "id": { "$ref": "#/$defs/ID" },
          "space": { "$ref": "#/$defs/ID" },
          "kind": { "enum": ["convex_mix", "quadratic_potential", "constraint"] },
          "inputs": { "type": "array", "items": { "$ref": "#/$defs/ID" } },
          "params": { "type": "object" },
          "energy": { "type": "string" }
        }
      }
    },

    "events": {
      "type": "array",
      "items": {
        "oneOf": [
          { "$ref": "#/$defs/EventEntry" },
          { "$ref": "#/$defs/GeometricIntent" }
        ]
      }
    }
  }
}
```

**Purpose**: Universal representation for geometric computations
**Key Features**:
- Manifold-agnostic design
- Extensible operation types
- PhysIR/CausalIR compatibility
- Backward CGIR compatibility

#### CGIR Builder
```python
class CGIRBuilder:
    def __init__(self, version: str = "0.1.0"):
        self.version = version
        self.spaces = []
        self.state = []
        self.interactions = []
        self.operators = []
        self.intents = []

    def add_space(self, space_def: SpaceDefinition):
        self.spaces.append(space_def)
        return self

    def add_state_variable(self, var: StateVariable):
        self.state.append(var)
        return self

    def add_interaction(self, interaction: Interaction):
        self.interactions.append(interaction)
        return self

    def simulate(self, steps: int = 100, dt: float = 0.01) -> List[Dict]:
        """Run geometric simulation over time steps."""
        current_state = {var.id: var.value for var in self.state}
        trajectory = []

        for step in range(steps):
            # Record state
            trajectory.append({
                "step": step,
                "time": step * dt,
                "state": current_state.copy()
            })

            # Process interactions
            for interaction in self.interactions:
                self._process_interaction(interaction, current_state)

            # Process intents
            for intent in self.intents:
                if intent.time <= step * dt:
                    self._process_intent(intent, current_state)

        return trajectory
```

**Purpose**: Programmatic construction of geometric computations
**Key Features**:
- Fluent builder API
- Simulation execution
- JSON serialization/deserialization

### Language SDKs

#### Python SDK Structure
```
oklab_grounding/
├── __init__.py          # Public API exports
├── space.py            # Core abstractions
├── oklab.py            # OKLab implementation
├── cgir.py             # Geometric IR builder
├── verification.py     # Runtime verification
├── server.py           # HTTP API server
├── numeric.py          # Utility functions
├── tests/              # Comprehensive test suite
├── docs/               # Documentation
├── examples.py         # Usage examples
├── pyproject.toml      # Packaging
└── README.md           # User documentation
```

#### TypeScript SDK Structure
```
webapp/packages/grounding/
├── src/
│   ├── index.ts        # Public API exports
│   ├── space.ts        # Core abstractions
│   ├── oklab.ts        # OKLab implementation
│   ├── ir.ts           # Geometric IR types/builder
│   └── space.test.ts   # Tests
├── package.json        # NPM packaging
├── tsconfig.json       # TypeScript configuration
└── README.md           # Package documentation
```

**Purpose**: Language-specific interfaces with consistent semantics
**Key Features**:
- Idiomatic APIs for each language
- Type safety (TypeScript) vs flexibility (Python)
- Comprehensive test coverage
- Documentation and examples

### HTTP Service Layer

#### REST API Design
```python
@app.route('/spaces/oklab', methods=['POST'])
def create_space():
    # Create OKLab space instance
    pass

@app.route('/groundings/<grounding_id>/bind', methods=['POST'])
def bind_symbol(grounding_id):
    # Bind symbol to region
    pass

@app.route('/groundings/<grounding_id>/query/nearest', methods=['POST'])
def query_nearest(grounding_id):
    # Find nearest symbol to point
    pass

@app.route('/spaces/oklab/mix', methods=['POST'])
def mix_colors():
    # Perform color mixing
    pass

@app.route('/cgir/simulate', methods=['POST'])
def simulate_cgir():
    # Run CGIR simulation
    pass
```

**Purpose**: Cross-language interoperability
**Key Features**:
- RESTful API design
- JSON request/response format
- Comprehensive error handling
- Stateless operations

## Data Flow Architecture

### Symbol Grounding Pipeline
```
User Input
    ↓
Symbol Parsing
    ↓
Grounding Lookup
    ↓
Region Containment Check
    ↓
Perceptual Validation
    ↓
Application Response
```

### Geometric Computation Pipeline
```
CGIR Definition
    ↓
Space Validation
    ↓
State Initialization
    ↓
Interaction Processing
    ↓
Intent Execution
    ↓
Trajectory Generation
    ↓
Result Analysis
```

### Verification Pipeline
```
Code Execution
    ↓
Property Checking
    ↓
Formal Verification
    ↓
Error Reporting
    ↓
Correctness Assurance
```

## Performance Characteristics

### Time Complexity
- **Distance Calculation**: O(1) - Simple coordinate differences
- **Region Containment**: O(1) - Spherical boundary checks
- **Symbol Classification**: O(n) - Linear search over regions
- **Color Mixing**: O(n) - Linear combination of inputs
- **Simulation**: O(steps × interactions) - Configurable complexity

### Space Complexity
- **Core Data Structures**: O(n) for symbols and regions
- **Geometric IR**: O(state + interactions + intents)
- **Trajectory Storage**: O(steps × state_size)

### Optimization Opportunities
- **Spatial Indexing**: R-tree or k-d tree for region queries
- **Caching**: LRU cache for repeated distance calculations
- **Vectorization**: NumPy acceleration for batch operations
- **GPU Acceleration**: CUDA/OpenCL for large-scale simulations

## Security Considerations

### Input Validation
- **Color Bounds Checking**: Prevent invalid OKLab coordinates
- **Weight Normalization**: Ensure mixing weights are valid
- **Schema Validation**: JSON schema enforcement for CGIR inputs

### Resource Protection
- **Rate Limiting**: Prevent abuse of computational resources
- **Timeout Controls**: Limit simulation execution time
- **Memory Bounds**: Prevent excessive memory usage

### Error Handling
- **Graceful Degradation**: Meaningful error messages without information leakage
- **Logging**: Comprehensive audit trails for debugging
- **Recovery**: Automatic cleanup on failures

## Extensibility Mechanisms

### Adding New Spaces
```python
class CustomSpace(GroundSpace[CustomPoint]):
    def distance(self, a, b): # Implement custom metric
    def mix(self, points, weights): # Implement custom mixing
    def validate(self, point): # Implement custom validation
```

### Adding New Region Types
```python
class CustomRegion(GroundRegion[OKLab]):
    def contains(self, point): # Implement custom containment logic
```

### Adding New Operations
```python
# Extend CGIRBuilder with custom operations
def add_custom_operation(self, operation_def):
    # Custom operation processing
    pass
```

## Deployment Architecture

### Python Package Distribution
- **PyPI Publication**: `pip install oklab-grounding`
- **Wheel Distribution**: Platform-specific binaries
- **Source Distribution**: Universal fallback

### TypeScript Package Distribution
- **NPM Registry**: `npm install @oklab/grounding`
- **ESM/CommonJS**: Dual module format support
- **Type Definitions**: Complete TypeScript support

### Container Deployment
```dockerfile
FROM python:3.9-slim

# Install framework
RUN pip install oklab-grounding

# Copy application
COPY app.py /app/

# Expose API port
EXPOSE 8000

# Run grounding server
CMD ["python", "-m", "oklab_grounding"]
```

## Monitoring and Observability

### Metrics Collection
- **API Usage**: Request counts, response times, error rates
- **Simulation Performance**: Steps per second, memory usage
- **Verification Success**: Property check pass/fail rates

### Logging Integration
- **Structured Logging**: JSON format with correlation IDs
- **Error Tracking**: Comprehensive error context and stack traces
- **Performance Monitoring**: Timing and resource usage metrics

### Health Checks
- **Dependency Validation**: Coq theorem checker availability
- **Space Consistency**: Automatic validation of configured spaces
- **API Responsiveness**: Synthetic transaction monitoring

This architecture provides a solid foundation for perceptual symbol grounding applications, balancing formal correctness with practical usability across multiple programming languages and deployment environments.
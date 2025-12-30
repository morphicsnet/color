# OKLab Grounding Framework

A framework for symbol grounding over perceptual spaces, providing formal guarantees through Coq proofs and executable implementations in Python and TypeScript.

## What is Symbol Grounding?

Symbol grounding is the problem of connecting abstract symbols (like words or concepts) to concrete perceptual representations in the physical world. This framework provides a structured approach using geometric spaces where:

- **Spaces**: Perceptual manifolds with distance metrics and operations
- **Symbols**: Discrete identifiers for concepts
- **Groundings**: Mappings from symbols to regions in perceptual space
- **Operations**: Mixing, similarity, and dynamic evolution of grounded representations

## Key Features

- **Formal Guarantees**: Core abstractions proved in Coq, extracted to executable code
- **Perceptual Foundation**: OKLab color space provides uniform perceptual distances
- **Geometric IR**: CGIR (Color Geometry Intermediate Representation) generalized to support arbitrary manifolds
- **Multi-Language**: Clean APIs in Python and TypeScript
- **Verification**: Runtime checks ensuring operations respect formal properties
- **HTTP Service**: REST API for cross-language interoperability

## Installation

### Python Package

```bash
pip install oklab-grounding
```

Or from source:
```bash
git clone <repository>
cd oklab_grounding
pip install -r requirements.txt
pip install -e .
```

### TypeScript Package

```bash
npm install @oklab/grounding
```

## Quick Start

### Python: Basic Grounding

```python
from oklab_grounding import OKLabSpace, Grounding

# Create an OKLab perceptual space
space = OKLabSpace()

# Create a grounding that maps symbols to regions
grounding = Grounding(space)

# Bind symbols to color regions
from oklab_grounding import OKLab, SphericalRegion

red_region = SphericalRegion(OKLab(L=0.5, a=0.3, b=0.2), radius=0.1, space=space)
grounding.bind_region("danger", red_region)

blue_region = SphericalRegion(OKLab(L=0.4, a=-0.1, b=-0.3), radius=0.1, space=space)
grounding.bind_region("calm", blue_region)

# Query relationships
test_color = OKLab(L=0.48, a=0.25, b=0.18)  # Slightly reddish color
nearest = grounding.nearest_symbol(test_color)
print(f"Color is closest to: {nearest}")  # "danger"

# Mix colors perceptually
colors = [OKLab(L=0.5, a=0.3, b=0.2), OKLab(L=0.4, a=-0.1, b=-0.3)]
weights = [0.6, 0.4]
mixed = space.mix(colors, weights)
print(f"Mixed color: L={mixed.L:.3f}, a={mixed.a:.3f}, b={mixed.b:.3f}")
```

### TypeScript: React Integration

```typescript
import { OKLabSpace, Grounding, type OKLab } from '@oklab/grounding';

const space = new OKLabSpace();
const grounding = new Grounding(space);

// Bind semantic colors
const errorColor: OKLab = { L: 0.5, a: 0.3, b: 0.2 };
const successColor: OKLab = { L: 0.6, a: -0.2, b: 0.2 };

grounding.bindRegion("error", {
  contains: (point) => space.distance(point, errorColor) < 0.1
});

grounding.bindRegion("success", {
  contains: (point) => space.distance(point, successColor) < 0.1
});

// Use in component
function StatusIndicator({ status }: { status: 'error' | 'success' }) {
  const baseColor = status === 'error' ? errorColor : successColor;
  const uiColor = space.mix([baseColor, { L: 0.9, a: 0, b: 0 }], [0.7, 0.3]);

  return (
    <div
      style={{
        backgroundColor: `oklab(${uiColor.L} ${uiColor.a} ${uiColor.b})`,
        padding: '1rem'
      }}
    >
      {status.toUpperCase()}
    </div>
  );
}
```

### CGIR: Geometric Computations

```python
from oklab_grounding import CGIRBuilder, SpaceDefinition, StateVariable

# Create a CGIR with generalized geometric spaces
cgir = CGIRBuilder("1.0.0")

# Define OKLab space
oklab_space = SpaceDefinition(
    id="oklab",
    kind="riemannian",
    dim=3,
    coords="OKLab",
    metric="oklab_canonical"
)
cgir.add_space(oklab_space)

# Add state variables (neurons/colors)
cgir.add_state_variable(StateVariable(
    id="color1",
    space="oklab",
    kind="point",
    value={"L": 0.7, "a": 0.1, "b": 0.2}
))

# Export as JSON
cgir_json = cgir.to_json()
print(cgir_json)
```

## Architecture

The framework provides layered abstractions:

1. **Formal Layer (Coq)**: Mathematical definitions and proofs
2. **Core Runtime**: Language-agnostic interfaces (distance, mix, validate)
3. **Geometric IR**: JSON-based intermediate representation
4. **SDKs**: Python and TypeScript implementations
5. **Services**: HTTP APIs for cross-language usage

## Verification & Guarantees

All operations can be verified against formal properties:

```python
from oklab_grounding import verify_oklab_consistency, OKLabVerifier

# Verify space properties
space = OKLabSpace()
colors = [OKLab(L=0.5, a=0.1, b=0.2), OKLab(L=0.6, a=-0.1, b=0.1)]
verify_oklab_consistency(space, colors)  # Raises VerificationError if invalid

# Custom verification
verifier = OKLabVerifier(space)
verifier.verify_oklab_bounds(colors)
verifier.verify_color_mixing_properties(colors, [0.5, 0.5])
```

## HTTP Service

Run a server for cross-language access:

```bash
python -m oklab_grounding --port 8000
```

API endpoints:
- `POST /spaces/oklab` - Create space
- `POST /groundings/{id}/bind` - Bind symbols
- `POST /groundings/{id}/query/nearest` - Query grounding
- `POST /cgir/simulate` - Run CGIR simulations

Example request:
```bash
curl -X POST http://localhost:8000/spaces/oklab/mix \
  -H "Content-Type: application/json" \
  -d '{"colors": [{"L": 0.5, "a": 0.3, "b": 0.2}], "weights": [1.0]}'
```

## Use Cases

### UI Design Systems
Ground color tokens in perceptual space for consistent theming:

```python
# Define semantic color regions
grounding.bind_region("primary", primary_region)
grounding.bind_region("secondary", secondary_region)

# Generate variants automatically
def generate_variant(base_symbol: str, lightness_offset: float):
    base_region = grounding.get_region(base_symbol)
    # Implementation creates lighter/darker variants within perceptual bounds
```

### Neurosymbolic AI
Model concept blending and composition:

```python
# Ground concepts in color space
grounding.bind_region("hot", red_region)
grounding.bind_region("cold", blue_region)

# Compose new concepts
warm_color = space.mix([red, blue], [0.6, 0.4])
new_concept = grounding.nearest_symbol(warm_color)  # Might recognize as "warm"
```

### Research Applications
Test hypotheses about perceptual grounding:

```python
# Measure how well color categories align with linguistic boundaries
def evaluate_category_alignment(category_colors, linguistic_boundaries):
    # Implementation measures alignment between perceptual clusters and language
    pass
```

## Contributing

The framework is built on formal methods:
- Core abstractions defined in `coq/Color/Core.v`
- Properties proved in Coq, extracted to executable code
- Runtime verification ensures correctness

See the main repository for contribution guidelines and formal specification details.

## License

[License information]
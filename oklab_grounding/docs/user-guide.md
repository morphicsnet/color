# OKLab Grounding Framework User Guide

This guide provides comprehensive tutorials and examples for using the OKLab Grounding Framework to build applications with symbol grounding over perceptual spaces.

## Table of Contents

- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Tutorial: Semantic Color Grounding](#tutorial-semantic-color-grounding)
- [Tutorial: Neurosymbolic Simulation](#tutorial-neurosymbolic-simulation)
- [Tutorial: Multi-Language Integration](#tutorial-multi-language-integration)
- [Advanced Patterns](#advanced-patterns)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Installation

```bash
# Python
pip install oklab-grounding

# TypeScript
npm install @oklab/grounding
```

### Hello World

```python
from oklab_grounding import OKLabSpace, Grounding, OKLab

# Create a perceptual space
space = OKLabSpace()

# Create a grounding that maps symbols to regions
grounding = Grounding(space)

# Define a color region for "red"
red_color = OKLab(L=0.5, a=0.3, b=0.2)
from oklab_grounding import SphericalRegion
red_region = SphericalRegion(red_color, radius=0.1, space=space)

# Bind the symbol
grounding.bind_region("red", red_region)

# Query: what symbol does this color belong to?
test_color = OKLab(L=0.52, a=0.28, b=0.18)
symbol = grounding.nearest_symbol(test_color)
print(f"Color belongs to: {symbol}")  # "red"
```

## Core Concepts

### Spaces
A **space** defines a perceptual manifold where symbols can be grounded. It provides:
- Distance metric for measuring perceptual similarity
- Mixing operation for combining perceptions
- Validation for ensuring points are within valid bounds

### Symbols
**Symbols** are discrete identifiers (strings) that represent concepts like "danger", "safe", "hot", "cold", etc.

### Regions
A **region** defines the geometric extent of a symbol in perceptual space. Regions can be:
- Spherical (circular) areas around a center point
- Custom shapes defined by containment predicates

### Grounding
A **grounding** maps symbols to regions in a space, enabling:
- Symbol lookup from perceptions
- Similarity calculations between symbols
- Validation of perceptual consistency

## Tutorial: Semantic Color Grounding

Build a system that grounds semantic concepts in color space for consistent UI theming.

### Step 1: Define Semantic Concepts

```python
from oklab_grounding import OKLabSpace, Grounding, OKLab, SphericalRegion

# Initialize the space and grounding
space = OKLabSpace()
grounding = Grounding(space)

# Define canonical colors for UI semantics
semantic_colors = {
    "primary": OKLab(L=0.6, a=-0.1, b=0.1),    # Balanced blue
    "success": OKLab(L=0.7, a=-0.2, b=0.3),    # Greenish
    "warning": OKLab(L=0.8, a=0.1, b=0.4),     # Yellowish
    "error": OKLab(L=0.5, a=0.4, b=0.2),       # Reddish
    "neutral": OKLab(L=0.7, a=0.0, b=0.0)      # Gray
}

# Create regions for each semantic concept
for concept, color in semantic_colors.items():
    region = SphericalRegion(color, radius=0.15, space=space)
    grounding.bind_region(concept, region)
```

### Step 2: Classification and Validation

```python
def classify_color(color: OKLab) -> str:
    """Classify a color into the nearest semantic category."""
    return grounding.nearest_symbol(color) or "unknown"

def validate_color_consistency(color: OKLab, expected_category: str) -> bool:
    """Check if a color is perceptually consistent with its semantic category."""
    predicted = classify_color(color)
    return predicted == expected_category

# Test classification
test_colors = [
    OKLab(L=0.58, a=-0.08, b=0.12),  # Should be "primary"
    OKLab(L=0.68, a=-0.18, b=0.32),  # Should be "success"
]

for color in test_colors:
    category = classify_color(color)
    print(f"Color {color} classified as: {category}")
```

### Step 3: Generate Consistent Variants

```python
def generate_accent_variant(base_concept: str, intensity: float = 0.8) -> OKLab:
    """Generate an accent variant of a semantic color."""
    base_region = grounding.get_region(base_concept)

    # For spherical regions, we can access the center
    if hasattr(base_region, 'center'):
        base_color = base_region.center

        # Create a more saturated/darker variant
        accent_color = OKLab(
            L=max(0.1, base_color.L * intensity),  # Darker
            a=base_color.a * 1.2,                   # More saturated
            b=base_color.b * 1.2
        )

        # Validate the variant is still valid
        if space.validate(accent_color):
            return accent_color

    # Fallback to base color if variant generation fails
    return semantic_colors[base_concept]

# Generate accent variants for all semantic colors
accent_colors = {}
for concept in semantic_colors.keys():
    accent_colors[concept] = generate_accent_variant(concept)

print("Generated accent variants:")
for concept, color in accent_colors.items():
    print(f"  {concept}: {color}")
```

## Tutorial: Neurosymbolic Simulation

Create a dynamic system where symbols interact and evolve through geometric computation.

### Step 1: Set Up CGIR with State Variables

```python
from oklab_grounding import CGIRBuilder, StateVariable, Interaction

# Create a CGIR builder
cgir = CGIRBuilder("neurosymbolic-demo-v1.0")

# Define the OKLab space
cgir.add_space({
    "id": "oklab",
    "kind": "riemannian",
    "dim": 3,
    "coords": "OKLab",
    "metric": "oklab_canonical"
})

# Add state variables representing concepts
concepts = {
    "hot": {"L": 0.8, "a": 0.3, "b": 0.4},      # Bright red-orange
    "cold": {"L": 0.4, "a": -0.2, "b": -0.3},   # Dark blue-purple
    "warm": {"L": 0.6, "a": 0.1, "b": 0.2}      # Medium orange
}

for concept_name, color_data in concepts.items():
    state_var = StateVariable(
        id=concept_name,
        space="oklab",
        kind="neuron",
        value=color_data
    )
    cgir.add_state_variable(state_var)
```

### Step 2: Define Interactions Between Concepts

```python
# Define how concepts interact
# "warm" emerges from mixing "hot" and "cold"
warm_interaction = Interaction(
    id="warm_emergence",
    space="oklab",
    kind="convex_mix",
    inputs=["hot", "cold"],
    params={"policy": "normalize"}
)

cgir.add_interaction(warm_interaction)

# Add a constraint that keeps "warm" distinct from pure "hot"
constraint_interaction = Interaction(
    id="warm_distinction",
    space="oklab",
    kind="constraint",
    inputs=["hot", "warm"],
    energy="||hot - warm||^2"  # Energy increases as they get closer
)

cgir.add_interaction(constraint_interaction)
```

### Step 3: Run the Simulation

```python
# Run simulation for 50 steps
trajectory = cgir.simulate(steps=50, dt=0.02)

# Analyze how concepts evolve
print("Concept evolution over time:")
for step_data in trajectory[-5:]:  # Last 5 steps
    step = step_data["step"]
    time = step_data["time"]
    state = step_data["state"]

    print(f"Step {step} (t={time:.2f}):")
    for concept in ["hot", "cold", "warm"]:
        if concept in state:
            color = state[concept]
            print(f"  {concept}: L={color.get('L', 0):.3f}, a={color.get('a', 0):.3f}, b={color.get('b', 0):.3f}")

# Check if "warm" emerged as expected
final_warm = trajectory[-1]["state"].get("warm", {})
final_hot = trajectory[-1]["state"].get("hot", {})
final_cold = trajectory[-1]["state"].get("cold", {})

print(f"\nFinal concept positions:")
print(f"Hot: {final_hot}")
print(f"Cold: {final_cold}")
print(f"Warm: {final_warm}")

# Verify warm is between hot and cold
if final_warm and final_hot and final_cold:
    warm_L = (final_hot.get('L', 0) + final_cold.get('L', 0)) / 2
    print(f"Expected warm L: {warm_L:.3f}, actual: {final_warm.get('L', 0):.3f}")
```

### Step 4: Visualize the Trajectory

```python
import matplotlib.pyplot as plt

# Extract trajectories for each concept
hot_trajectory = [step["state"].get("hot", {}).get("L", 0) for step in trajectory]
cold_trajectory = [step["state"].get("cold", {}).get("L", 0) for step in trajectory]
warm_trajectory = [step["state"].get("warm", {}).get("L", 0) for step in trajectory]

times = [step["time"] for step in trajectory]

plt.figure(figsize=(10, 6))
plt.plot(times, hot_trajectory, 'r-', label='Hot', linewidth=2)
plt.plot(times, cold_trajectory, 'b-', label='Cold', linewidth=2)
plt.plot(times, warm_trajectory, 'orange', label='Warm', linewidth=2)
plt.xlabel('Time')
plt.ylabel('Lightness (L)')
plt.title('Concept Evolution in OKLab Space')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

## Tutorial: Multi-Language Integration

Use the framework across Python and TypeScript for full-stack grounding applications.

### Python Backend (Data Processing)

```python
# backend.py
from oklab_grounding import OKLabSpace, Grounding, SphericalRegion, OKLab
from oklab_grounding import verify_oklab_consistency

class GroundingService:
    def __init__(self):
        self.space = OKLabSpace()
        self.grounding = Grounding(self.space)
        self._setup_semantic_regions()

    def _setup_semantic_regions(self):
        """Initialize semantic color regions."""
        regions = {
            "danger": OKLab(L=0.5, a=0.4, b=0.2),
            "warning": OKLab(L=0.75, a=0.2, b=0.4),
            "success": OKLab(L=0.65, a=-0.3, b=0.4),
            "info": OKLab(L=0.55, a=-0.2, b=-0.3)
        }

        for name, center in regions.items():
            region = SphericalRegion(center, radius=0.12, self.space)
            self.grounding.bind_region(name, region)

    def classify_color(self, r: float, g: float, b: float) -> str:
        """Classify RGB color to semantic category."""
        # Convert RGB to OKLab (simplified conversion)
        # In practice, use proper RGB->OKLab conversion
        oklab_color = OKLab(L=(r + g + b) / 3, a=r - g, b=(2*b - r - g) / 3)

        # Validate the color is in bounds
        if not self.space.validate(oklab_color):
            return "invalid"

        return self.grounding.nearest_symbol(oklab_color) or "unknown"

    def get_similar_concepts(self, concept: str) -> list:
        """Find concepts similar to the given one."""
        similarities = []
        try:
            for other_concept in ["danger", "warning", "success", "info"]:
                if other_concept != concept:
                    similarity = self.grounding.similarity(concept, other_concept)
                    similarities.append((other_concept, similarity))
        except ValueError:
            pass  # Concept not found

        return sorted(similarities, key=lambda x: x[1], reverse=True)

# Create global service instance
grounding_service = GroundingService()
```

### TypeScript Frontend (React Integration)

```typescript
// components/ColorClassifier.tsx
import React, { useState } from 'react';
import { OKLabSpace, Grounding, SphericalRegion, type OKLab } from '@oklab/grounding';

interface ColorClassifierProps {
  onClassification: (result: string) => void;
}

export const ColorClassifier: React.FC<ColorClassifierProps> = ({ onClassification }) => {
  const [selectedColor, setSelectedColor] = useState<string>('#ff6b6b');

  const classifyColor = async () => {
    // Convert hex to RGB
    const r = parseInt(selectedColor.slice(1, 3), 16) / 255;
    const g = parseInt(selectedColor.slice(3, 5), 16) / 255;
    const b = parseInt(selectedColor.slice(5, 7), 16) / 255;

    try {
      // Call backend API
      const response = await fetch('/api/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ r, g, b })
      });

      const result = await response.json();
      onClassification(result.category);
    } catch (error) {
      console.error('Classification failed:', error);
    }
  };

  return (
    <div className="color-classifier">
      <input
        type="color"
        value={selectedColor}
        onChange={(e) => setSelectedColor(e.target.value)}
      />
      <button onClick={classifyColor}>Classify Color</button>
    </div>
  );
};
```

### HTTP API Integration

```python
# api.py
from flask import Flask, request, jsonify
from backend import grounding_service

app = Flask(__name__)

@app.route('/api/classify', methods=['POST'])
def classify():
    data = request.get_json()
    r, g, b = data['r'], data['g'], data['b']

    category = grounding_service.classify_color(r, g, b)
    return jsonify({'category': category})

@app.route('/api/similar/<concept>', methods=['GET'])
def get_similar(concept: str):
    similar = grounding_service.get_similar_concepts(concept)
    return jsonify({
        'concept': concept,
        'similar': [{'name': name, 'similarity': sim} for name, sim in similar]
    })

if __name__ == '__main__':
    app.run(port=5000)
```

## Advanced Patterns

### Custom Region Types

```python
from typing import List
from oklab_grounding import GroundRegion, OKLabSpace, OKLab

class EllipsoidalRegion(GroundRegion[OKLab]):
    def __init__(self, center: OKLab, radii: List[float], space: OKLabSpace):
        self.center = center
        self.radii = radii  # [radius_L, radius_a, radius_b]
        self.space = space

    def contains(self, point: OKLab) -> bool:
        # Check if point is within ellipsoid
        dl = (point.L - self.center.L) / self.radii[0]
        da = (point.a - self.center.a) / self.radii[1]
        db = (point.b - self.center.b) / self.radii[2]

        return (dl * dl + da * da + db * db) <= 1.0
```

### Performance Optimization

```python
from functools import lru_cache
from oklab_grounding import Grounding

class CachedGrounding(Grounding):
    def __init__(self, space, max_cache_size=1000):
        super().__init__(space)
        self._cache = {}

    @lru_cache(maxsize=1000)
    def nearest_symbol_cached(self, point_tuple):
        # Convert OKLab to tuple for caching
        point = OKLab(*point_tuple)
        return self.nearest_symbol(point)

    def nearest_symbol(self, point):
        # Use cached version
        point_tuple = (point.L, point.a, point.b)
        return self.nearest_symbol_cached(point_tuple)
```

### Verification Integration

```python
from oklab_grounding import verify_oklab_consistency, VerificationError

def safe_color_operation(operation_func):
    """Decorator that verifies OKLab consistency."""
    def wrapper(*args, **kwargs):
        result = operation_func(*args, **kwargs)

        # Verify result is valid
        if isinstance(result, OKLab):
            colors = [result]
        elif isinstance(result, list) and all(isinstance(c, OKLab) for c in result):
            colors = result
        else:
            return result  # Not color-related

        try:
            space = OKLabSpace()
            verify_oklab_consistency(space, colors)
            return result
        except VerificationError as e:
            print(f"Verification failed: {e}")
            raise

    return wrapper

@safe_color_operation
def mix_colors(colors: List[OKLab], weights: List[float]) -> OKLab:
    space = OKLabSpace()
    return space.mix(colors, weights)
```

## Best Practices

### Space Design
- Choose spaces that match your perceptual domain (OKLab for colors, other manifolds for different modalities)
- Validate that your space's distance metric reflects human perception
- Ensure mixing operations preserve perceptual consistency

### Region Definition
- Use regions that are large enough to capture natural variation but small enough to maintain distinction
- Consider overlapping regions for fuzzy concepts
- Validate region definitions against human judgments when possible

### Performance Considerations
- Cache frequently accessed computations (distance calculations, region containment)
- Use efficient data structures for large numbers of symbols
- Profile geometric operations for optimization opportunities

### Error Handling
- Always validate inputs to grounding operations
- Provide meaningful error messages for debugging
- Gracefully handle edge cases (empty regions, invalid colors)

### Testing and Validation
- Use the verification layer to ensure mathematical correctness
- Test with edge cases (boundary colors, extreme weights)
- Validate against human perceptual judgments when possible

## Troubleshooting

### Common Issues

#### Import Errors
```python
# If you get import errors, check your PYTHONPATH
import sys
sys.path.insert(0, '/path/to/oklab_grounding')
from oklab_grounding import OKLabSpace
```

#### Invalid Colors
```python
# OKLab colors must be in valid ranges
color = OKLab(L=0.5, a=0.1, b=0.2)  # Valid
space = OKLabSpace()
assert space.validate(color)  # Should pass
```

#### No Matching Symbols
```python
# If nearest_symbol returns None, check:
# 1. Are any regions bound?
# 2. Is the query point valid?
# 3. Are region definitions appropriate?

grounding = Grounding(space)
print(f"Number of bound symbols: {len(list(grounding._regions.keys()))}")
```

#### Simulation Not Changing
```python
# If CGIR simulation doesn't evolve:
# 1. Check that interactions are defined
# 2. Verify state variables exist
# 3. Ensure intents are properly timed
trajectory = cgir.simulate(steps=10)
print("State changes:", [len(set(str(s) for s in step['state'].values())) for step in trajectory])
```

### Debug Tools

```python
def debug_grounding(grounding: Grounding, test_points: List[OKLab]):
    """Debug helper for grounding issues."""
    print("Grounding Debug Info:")
    print(f"Space type: {type(grounding.space)}")
    print(f"Number of symbols: {len(grounding._regions)}")

    for symbol in grounding._regions.keys():
        region = grounding.get_region(symbol)
        print(f"Symbol '{symbol}': region type {type(region)}")

    print("\nTesting query points:")
    for i, point in enumerate(test_points):
        symbol = grounding.nearest_symbol(point)
        print(f"Point {i}: {point} -> {symbol}")

# Usage
test_points = [OKLab(L=0.5, a=0.1, b=0.2), OKLab(L=0.7, a=-0.1, b=0.3)]
debug_grounding(grounding, test_points)
```

This comprehensive guide provides the foundation for building applications with the OKLab Grounding Framework. Start with the quick start examples, then progress through the tutorials to build increasingly sophisticated grounding systems.
"""
Usage examples and cookbook for the OKLab Grounding Framework.

This file demonstrates common patterns and use cases for symbol grounding
in perceptual spaces.
"""

from typing import List
try:
    # When run as part of package
    from .space import OKLabSpace, Grounding, SphericalRegion
    from .oklab import OKLab
    from .cgir import CGIRBuilder
    from .verification import verify_oklab_consistency
except ImportError:
    # When run as standalone script
    from space import OKLabSpace, Grounding, SphericalRegion
    from oklab import OKLab
    from cgir import CGIRBuilder
    from verification import verify_oklab_consistency

# Example 1: Basic Semantic Color Grounding
def example_semantic_colors():
    """
    Ground semantic concepts like "danger", "warning", "success" in color space.

    This demonstrates how UI design systems can maintain perceptual consistency
    across different color tokens.
    """
    print("=== Semantic Color Grounding ===")

    # Create OKLab space and grounding
    space = OKLabSpace()
    grounding = Grounding(space)

    # Define canonical colors for semantic concepts
    semantic_colors = {
        "danger": OKLab(L=0.5, a=0.3, b=0.2),    # Reddish
        "warning": OKLab(L=0.7, a=0.1, b=0.3),   # Orangeish
        "success": OKLab(L=0.6, a=-0.2, b=0.2),  # Greenish
        "info": OKLab(L=0.5, a=-0.1, b=-0.3),    # Blueish
        "neutral": OKLab(L=0.7, a=0, b=0)        # Grayish
    }

    # Bind concepts to spherical regions around canonical colors
    for concept, color in semantic_colors.items():
        region = SphericalRegion(color, radius=0.15, space=space)
        grounding.bind_region(concept, region)

    # Test classification
    test_colors = [
        OKLab(L=0.48, a=0.28, b=0.18),  # Danger-like
        OKLab(L=0.68, a=0.08, b=0.28),  # Warning-like
        OKLab(L=0.58, a=-0.18, b=0.18), # Success-like
    ]

    for i, test_color in enumerate(test_colors):
        nearest = grounding.nearest_symbol(test_color)
        print(".3f")

    # Generate UI variants by mixing with neutral
    neutral = semantic_colors["neutral"]
    for concept, base_color in semantic_colors.items():
        if concept != "neutral":
            # Create lighter variant
            light_variant = space.mix([base_color, neutral], [0.6, 0.4])
            print(".3f")

def example_neurosymbolic_simulation():
    """
    Demonstrate dynamic symbol composition using CGIR.

    This shows how concepts can be combined and evolve over time
    through neuron-like processing.
    """
    print("\n=== Neurosymbolic Simulation ===")

    # Build a CGIR with color neurons
    cgir = CGIRBuilder("example-v1.0")

    # Define OKLab space
    cgir.add_space({
        "id": "oklab",
        "kind": "riemannian",
        "dim": 3,
        "coords": "OKLab",
        "metric": "oklab_canonical"
    })

    # Add state variables (neurons)
    cgir.add_state_variable({
        "id": "hot_concept",
        "space": "oklab",
        "kind": "neuron",
        "value": {"L": 0.7, "a": 0.2, "b": 0.3}  # Warm red
    })

    cgir.add_state_variable({
        "id": "cold_concept",
        "space": "oklab",
        "kind": "neuron",
        "value": {"L": 0.5, "a": -0.1, "b": -0.3}  # Cool blue
    })

    cgir.add_state_variable({
        "id": "composed_concept",
        "space": "oklab",
        "kind": "neuron",
        "value": {"L": 0.6, "a": 0.05, "b": 0}  # Neutral starting point
    })

    # Add interaction: mix hot and cold concepts
    cgir.add_interaction({
        "id": "temperature_blend",
        "space": "oklab",
        "kind": "convex_mix",
        "inputs": ["hot_concept", "cold_concept"],
        "params": {"policy": "normalize"}
    })

    # Add geometric intent: inject composition result
    cgir.add_intent({
        "time": 0.0,
        "kind": "state_injection",
        "target": "composed_concept",
        "space": "oklab",
        "params": {
            "value": {"L": 0.6, "a": 0.05, "b": 0.02}
        }
    })

    # Simulate for a few steps
    trajectory = cgir.simulate(steps=5)
    print(f"Simulation trajectory: {len(trajectory)} steps")

    for step in trajectory[:3]:  # Show first 3 steps
        state = step["state"]
        hot = state.get("hot_concept", {})
        cold = state.get("cold_concept", {})
        composed = state.get("composed_concept", {})
        print(".3f")

def example_verification():
    """
    Demonstrate formal verification of grounding properties.

    Shows how to verify that implementations respect mathematically
    proved properties from Coq.
    """
    print("\n=== Formal Verification ===")

    space = OKLabSpace()

    # Create test colors
    test_colors = [
        OKLab(L=0.5, a=0.1, b=0.2),
        OKLab(L=0.6, a=-0.1, b=0.1),
        OKLab(L=0.7, a=0.05, b=-0.05),
    ]

    print("Testing OKLab space properties...")

    try:
        verify_oklab_consistency(space, test_colors)
        print("✓ All OKLab properties verified")
    except Exception as e:
        print(f"✗ Verification failed: {e}")

    # Test mix closure
    mixed = space.mix(test_colors, [0.4, 0.4, 0.2])
    print(".3f")

    # Verify mixed result is still valid
    if space.validate(mixed):
        print("✓ Mixed result remains in valid space")
    else:
        print("✗ Mixed result outside valid space")

def example_http_api_usage():
    """
    Example of using the grounding framework via HTTP API.

    Shows how other languages can access grounding functionality.
    """
    print("\n=== HTTP API Usage Example ===")
    print("""
# Start the grounding server
python -m oklab_grounding --port 8000

# Create a space
curl -X POST http://localhost:8000/spaces/oklab \\
  -H "Content-Type: application/json" \\
  -d '{"id": "my_space"}'

# Bind semantic colors
curl -X POST http://localhost:8000/groundings/default/bind \\
  -H "Content-Type: application/json" \\
  -d '{
    "symbol": "error",
    "region": {
      "center": {"L": 0.5, "a": 0.3, "b": 0.2},
      "radius": 0.1
    }
  }'

# Query nearest symbol
curl -X POST http://localhost:8000/groundings/default/query/nearest \\
  -H "Content-Type: application/json" \\
  -d '{"point": {"L": 0.48, "a": 0.28, "b": 0.18}}'

# Mix colors
curl -X POST http://localhost:8000/spaces/oklab/mix \\
  -H "Content-Type: application/json" \\
  -d '{
    "colors": [
      {"L": 0.5, "a": 0.3, "b": 0.2},
      {"L": 0.6, "a": -0.2, "b": 0.2}
    ],
    "weights": [0.6, 0.4]
  }'
""")

if __name__ == "__main__":
    example_semantic_colors()
    example_neurosymbolic_simulation()
    example_verification()
    example_http_api_usage()
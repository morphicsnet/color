# OKLab Grounding Framework Documentation

Welcome to the comprehensive documentation for the OKLab Grounding Framework, a toolkit for symbol grounding over perceptual spaces.

## Documentation Overview

This documentation is organized into several sections to help you understand and use the framework effectively:

### 🚀 Getting Started
- **[Main README](../README.md)** - Framework overview, quick start, and installation
- **[Installation Guide](installation.md)** - Detailed installation and deployment instructions
- **[User Guide](user-guide.md)** - Tutorials and examples for common use cases

### 📚 Reference Documentation
- **[API Reference](api.md)** - Complete API documentation for all components
- **[Architecture Guide](architecture.md)** - System architecture and design principles

### 🔧 Development & Operations
- **[Contributing Guidelines](../CONTRIBUTING.md)** - How to contribute to the framework
- **[Changelog](../CHANGELOG.md)** - Version history and release notes

## Quick Navigation

### For New Users
1. Start with the [Main README](../README.md) for an overview
2. Follow the [Installation Guide](installation.md) to set up your environment
3. Work through the [User Guide](user-guide.md) tutorials
4. Refer to the [API Reference](api.md) as needed

### For Developers
1. Read the [Architecture Guide](architecture.md) to understand the system design
2. Check the [API Reference](api.md) for implementation details
3. Follow the [Contributing Guidelines](../CONTRIBUTING.md) for development workflow

### For Operators
1. Use the [Installation Guide](installation.md) for deployment options
2. Monitor using the health check endpoints documented in the API reference

## Key Concepts

### Symbol Grounding
The process of connecting abstract symbols (like words or concepts) to concrete perceptual representations in continuous spaces.

### Perceptual Spaces
Mathematical spaces where perception happens, implemented with metrics for measuring similarity and operations for combining perceptions.

### OKLab Color Space
A perceptually uniform color space used as the primary implementation, providing accurate perceptual distance measurements.

### Geometric IR (CGIR)
An intermediate representation for describing geometric computations, supporting both legacy color operations and generalized manifold computations.

## Framework Components

### Core Runtime
- **GroundSpace**: Abstract interface for perceptual spaces
- **GroundRegion**: Geometric regions defining symbol extents
- **Grounding**: Mappings from symbols to regions with query operations

### Language SDKs
- **Python Package**: `oklab_grounding` - Full-featured scientific computing SDK
- **TypeScript Package**: `@oklab/grounding` - Type-safe web application SDK

### Tools & Services
- **CLI Tools**: Command-line utilities for validation, simulation, and processing
- **HTTP API**: REST service for cross-language interoperability
- **Verification Layer**: Runtime checks ensuring formal property compliance

## Example Usage Patterns

### Simple Classification
```python
from oklab_grounding import OKLabSpace, Grounding, SphericalRegion, OKLab

space = OKLabSpace()
grounding = Grounding(space)

# Define a region for "red"
red_region = SphericalRegion(OKLab(L=0.5, a=0.3, b=0.2), 0.1, space)
grounding.bind_region("red", red_region)

# Classify a color
test_color = OKLab(L=0.52, a=0.28, b=0.18)
category = grounding.nearest_symbol(test_color)
print(f"Color classified as: {category}")
```

### Neurosymbolic Simulation
```python
from oklab_grounding import CGIRBuilder, StateVariable, Interaction

cgir = CGIRBuilder()
cgir.add_state_variable(StateVariable(
    id="concept", space="oklab", kind="neuron",
    value={"L": 0.6, "a": 0.1, "b": 0.2}
))

trajectory = cgir.simulate(steps=100)
for step in trajectory[-5:]:
    print(f"Step {step['step']}: {step['state']}")
```

### Web Integration
```typescript
import { OKLabSpace, Grounding } from '@oklab/grounding';

const space = new OKLabSpace();
const grounding = new Grounding(space);

// Use in React components, data visualization, etc.
```

## Need Help?

- **📖 Documentation Issues**: Report problems with docs on [GitHub Issues](https://github.com/your-org/oklab-grounding/issues)
- **💬 Questions**: Join community discussions or ask on [GitHub Discussions](https://github.com/your-org/oklab-grounding/discussions)
- **🐛 Bug Reports**: File detailed bug reports with reproduction steps
- **✨ Feature Requests**: Suggest new features and improvements

## Version Information

- **Current Version**: 0.1.0
- **Python Support**: 3.8+
- **TypeScript Support**: 4.5+
- **License**: MIT

---

*This framework bridges formal mathematical foundations with practical perceptual computing applications.*
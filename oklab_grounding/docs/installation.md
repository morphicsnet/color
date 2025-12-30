# Installation and Deployment Guide

This guide covers installing, deploying, and maintaining the OKLab Grounding Framework.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Python Installation](#python-installation)
- [TypeScript Installation](#typescript-installation)
- [Development Setup](#development-setup)
- [Deployment Options](#deployment-options)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Upgrading](#upgrading)

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Node.js**: 18.0 or higher (for TypeScript development)
- **Coq**: 8.19+ (optional, for formal verification development)

### Operating Systems
- **Linux**: Ubuntu 20.04+, CentOS 8+, Fedora 34+
- **macOS**: 11.0+ (Intel/Apple Silicon)
- **Windows**: 10+ with WSL2 or native Python/Node.js

## Python Installation

### Option 1: From PyPI (Recommended)

```bash
# Install the latest stable version
pip install oklab-grounding

# Or with optional HTTP server dependencies
pip install oklab-grounding[server]
```

### Option 2: From Source

```bash
# Clone the repository
git clone https://github.com/your-org/oklab-grounding.git
cd oklab-grounding

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Optional: Install development dependencies
pip install -e ".[dev]"
```

### Option 3: Using Conda

```bash
# Create conda environment
conda create -n oklab-grounding python=3.9
conda activate oklab-grounding

# Install from PyPI
pip install oklab-grounding
```

### Verification

```bash
python -c "import oklab_grounding; print('✅ OKLab Grounding installed successfully')"
```

## TypeScript Installation

### Option 1: From NPM (Recommended)

```bash
# Install the package
npm install @oklab/grounding

# Or with Yarn
yarn add @oklab/grounding

# Or with pnpm
pnpm add @oklab/grounding
```

### Option 2: From Source (Monorepo)

```bash
# Clone the repository
git clone https://github.com/your-org/oklab-grounding.git
cd oklab-grounding/webapp

# Install dependencies
npm install

# Build the grounding package
cd packages/grounding
npm run build
```

### TypeScript Configuration

Add to your `tsconfig.json`:

```json
{
  "compilerOptions": {
    "moduleResolution": "node",
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true
  }
}
```

### Verification

```typescript
import { OKLabSpace, Grounding } from '@oklab/grounding';

const space = new OKLabSpace();
const grounding = new Grounding(space);
console.log('✅ OKLab Grounding TypeScript package working');
```

## Development Setup

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/oklab-grounding.git
cd oklab-grounding

# Python development setup
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# TypeScript development setup
cd webapp
npm install
```

### Running Tests

```bash
# Python tests
cd oklab_grounding
python -m pytest tests/ -v

# TypeScript tests
cd webapp/packages/grounding
npm test
```

### Building Documentation

```bash
# Python documentation
cd oklab_grounding/docs
# Documentation is in Markdown format

# TypeScript documentation
cd webapp/packages/grounding
npm run build  # Generates .d.ts files
```

### Code Quality Checks

```bash
# Python linting and formatting
cd oklab_grounding
black .  # Format code
isort .  # Sort imports
mypy .   # Type checking

# TypeScript linting
cd webapp/packages/grounding
npm run lint
```

## Deployment Options

### Option 1: Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY oklab_grounding/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY oklab_grounding/ .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "oklab_grounding"]
```

#### Docker Compose
```yaml
version: '3.8'
services:
  grounding-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Build and Run
```bash
# Build the image
docker build -t oklab-grounding .

# Run the container
docker run -p 8000:8000 oklab-grounding

# Or using docker-compose
docker-compose up -d
```

### Option 2: Kubernetes Deployment

#### Deployment Manifest
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oklab-grounding
spec:
  replicas: 3
  selector:
    matchLabels:
      app: oklab-grounding
  template:
    metadata:
      labels:
        app: oklab-grounding
    spec:
      containers:
      - name: grounding-api
        image: your-registry/oklab-grounding:latest
        ports:
        - containerPort: 8000
        env:
        - name: PYTHONPATH
          value: "/app"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### Service Manifest
```yaml
apiVersion: v1
kind: Service
metadata:
  name: oklab-grounding-service
spec:
  selector:
    app: oklab-grounding
  ports:
    - port: 80
      targetPort: 8000
  type: LoadBalancer
```

### Option 3: Serverless Deployment

#### AWS Lambda (Python)
```python
# lambda_function.py
from oklab_grounding import OKLabSpace, Grounding, SphericalRegion, OKLab

# Global instances for reuse
space = OKLabSpace()
grounding = Grounding(space)

# Initialize semantic regions
def initialize_grounding():
    global grounding
    regions = {
        "danger": OKLab(L=0.5, a=0.4, b=0.2),
        "success": OKLab(L=0.65, a=-0.3, b=0.4),
        "warning": OKLab(L=0.75, a=0.2, b=0.4)
    }

    for name, color in regions.items():
        region = SphericalRegion(color, radius=0.15, space=space)
        grounding.bind_region(name, region)

initialize_grounding()

def lambda_handler(event, context):
    # Extract color from event
    r = float(event.get('r', 0.5))
    g = float(event.get('g', 0.5))
    b = float(event.get('b', 0.5))

    # Simple RGB to OKLab conversion (simplified)
    oklab_color = OKLab(L=(r + g + b) / 3, a=r - g, b=(2*b - r - g) / 3)

    # Classify
    category = grounding.nearest_symbol(oklab_color) or "unknown"

    return {
        'statusCode': 200,
        'body': {
            'category': category,
            'color': {'L': oklab_color.L, 'a': oklab_color.a, 'b': oklab_color.b}
        }
    }
```

#### Vercel (TypeScript)
```typescript
// api/classify.ts
import { OKLabSpace, Grounding, SphericalRegion, type OKLab } from '@oklab/grounding';

// Initialize globally
const space = new OKLabSpace();
const grounding = new Grounding(space);

// Initialize semantic regions
const regions = {
  danger: { L: 0.5, a: 0.4, b: 0.2 },
  success: { L: 0.65, a: -0.3, b: 0.4 },
  warning: { L: 0.75, a: 0.2, b: 0.4 }
};

for (const [name, color] of Object.entries(regions)) {
  const region = new SphericalRegion(color as OKLab, 0.15, space);
  grounding.bindRegion(name, region);
}

export default function handler(req, res) {
  const { r = 0.5, g = 0.5, b = 0.5 } = req.query;

  // Simple RGB to OKLab conversion
  const oklabColor = {
    L: (r + g + b) / 3,
    a: r - g,
    b: (2 * b - r - g) / 3
  };

  const category = grounding.nearestSymbol(oklabColor) || 'unknown';

  res.status(200).json({
    category,
    color: oklabColor
  });
}
```

## Configuration

### Environment Variables

```bash
# Server configuration
GROUNDING_HOST=0.0.0.0
GROUNDING_PORT=8000
GROUNDING_DEBUG=false

# Performance tuning
GROUNDING_MAX_CACHE_SIZE=1000
GROUNDING_SIMULATION_TIMEOUT=30

# Logging
GROUNDING_LOG_LEVEL=INFO
GROUNDING_LOG_FORMAT=json
```

### Python Configuration

```python
import os
from oklab_grounding import OKLabSpace, Grounding

# Configure space with custom settings
space = OKLabSpace()

# Configure grounding with performance optimizations
grounding = Grounding(space)

# Custom region definitions
from oklab_grounding import SphericalRegion
region = SphericalRegion(
    center=OKLab(L=0.5, a=0.1, b=0.2),
    radius=float(os.getenv('REGION_RADIUS', '0.1')),
    space=space
)
```

### TypeScript Configuration

```typescript
import { OKLabSpace, Grounding } from '@oklab/grounding';

// Configure with custom settings
const space = new OKLabSpace();
const grounding = new Grounding(space);

// Environment-based configuration
const config = {
  regionRadius: parseFloat(process.env.REGION_RADIUS || '0.1'),
  maxCacheSize: parseInt(process.env.MAX_CACHE_SIZE || '1000')
};
```

## Troubleshooting

### Common Installation Issues

#### Python Import Errors
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall package
pip uninstall oklab-grounding
pip install oklab-grounding

# Check for conflicting packages
pip list | grep grounding
```

#### TypeScript Module Resolution
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check TypeScript configuration
npx tsc --showConfig
```

#### Coq Dependency Issues
```bash
# Install Coq (Ubuntu/Debian)
sudo apt-get install coq

# Install Coq (macOS with Homebrew)
brew install coq

# Verify Coq installation
coqc --version
```

### Runtime Issues

#### Memory Usage
```python
# Monitor memory usage
import psutil
import os

process = psutil.Process(os.getpid())
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

#### Performance Profiling
```python
import cProfile
import pstats

def profile_function():
    # Your grounding code here
    pass

cProfile.run('profile_function()', 'profile.prof')
stats = pstats.Stats('profile.prof')
stats.sort_stats('cumulative').print_stats(10)
```

### Network Issues (HTTP API)

#### Connection Refused
```bash
# Check if server is running
curl http://localhost:8000/health

# Check server logs
docker logs <container_name>

# Verify port binding
netstat -tlnp | grep 8000
```

#### Timeout Errors
```python
import requests

# Add timeout to requests
response = requests.post(
    'http://localhost:8000/api/classify',
    json={'r': 0.5, 'g': 0.5, 'b': 0.5},
    timeout=10  # 10 second timeout
)
```

## Upgrading

### From Previous Versions

#### Version 0.0.x to 0.1.x
```bash
# Backup existing configurations
cp config.json config.json.backup

# Upgrade package
pip install --upgrade oklab-grounding

# Update import statements
# Old: from oklab_grounding.core import OKLabSpace
# New: from oklab_grounding import OKLabSpace

# Update CGIR format (automatic conversion available)
python -c "
from oklab_grounding import CGIRBuilder
# Migration utilities available in CGIRBuilder.from_legacy_format()
"
```

### Migration Guide

```python
# Automatic migration from legacy format
from oklab_grounding import CGIRBuilder

# Load old CGIR
# Migration utilities will handle format updates
builder = CGIRBuilder.from_legacy_format(legacy_cgir_data)
new_cgir = builder.to_dict()
```

### Breaking Changes

#### Version 0.1.0
- **CGIR Schema**: Extended to support generalized geometric IR
- **API Changes**: Some method signatures updated for consistency
- **Import Path**: Core modules moved to package root
- **Dependencies**: Added optional Flask dependency for server mode

#### Migration Script
```python
#!/usr/bin/env python3
"""
Migration script for OKLab Grounding Framework v0.1.x
"""

from pathlib import Path
import json

def migrate_cgir_files(directory: str):
    """Migrate CGIR files to new format."""
    cgir_dir = Path(directory)

    for cgir_file in cgir_dir.glob("*.json"):
        with open(cgir_file, 'r') as f:
            data = json.load(f)

        # Add version if missing
        if 'cgir_version' not in data:
            data['cgir_version'] = '0.1.0'

        # Migrate legacy format if needed
        if 'droplet' in data and 'spaces' not in data:
            # This is legacy CGIR, add default OKLab space
            data['spaces'] = [{
                'id': 'oklab',
                'kind': 'riemannian',
                'dim': 3,
                'coords': 'OKLab',
                'metric': 'oklab_canonical'
            }]

        # Write back migrated data
        with open(cgir_file, 'w') as f:
            json.dump(data, f, indent=2)

if __name__ == '__main__':
    migrate_cgir_files('path/to/cgir/files')
```

## Support and Contributing

### Getting Help
- **Documentation**: Check the [user guide](user-guide.md) and [API docs](api.md)
- **Issues**: Report bugs on [GitHub Issues](https://github.com/your-org/oklab-grounding/issues)
- **Discussions**: Join community discussions for questions

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.

### Security
Report security vulnerabilities to security@your-org.com

This installation guide ensures you can get the OKLab Grounding Framework up and running in your preferred environment, whether for development, testing, or production deployment.
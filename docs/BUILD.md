---
title: Build and Run Guide
description: Unified instructions to set up, build, run, and test Python CGIR tools, the TypeScript webapp, and Coq proof artifacts.
tags: [meta, build, run, python, typescript, coq]
source-pdf: null
last-updated: 2025-11-13
---
# Build and Run Guide

This guide provides end-to-end, runnable instructions for working with the Python CGIR tools, the TypeScript webapp monorepo, and Coq artifacts. All commands assume the repository root as the working directory unless noted.

## Table of Contents
- Prerequisites
- Python CGIR tools
- TypeScript webapp monorepo
- Coq build with dune
- Integrated workflow examples
- Troubleshooting

## Prerequisites

- Python 3.10+ with venv
- Node.js 18+ and npm 9+ (or compatible)
- Coq/Dune toolchain (Coq 8.19, dune 3.x recommended)
- macOS/Linux shell or Windows with a compatible shell environment

Paths referenced:
- CLIs and core (Python): [tools/cgir](tools/cgir)
- Webapp workspace: [webapp](webapp)
- Coq sources: [coq](coq)

## Python CGIR tools

Install and activate a virtual environment, then install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/cgir/requirements.txt
```

Key CLIs (runnable from repo root):
- Validate IR: [tools/cgir/cli_validate.py](tools/cgir/cli_validate.py)
- Simulate: [tools/cgir/cli_sim.py](tools/cgir/cli_sim.py)
- Train: [tools/cgir/cli_train.py](tools/cgir/cli_train.py)
- Visualize: [tools/cgir/cli_viz.py](tools/cgir/cli_viz.py)
- Verify: [tools/cgir/cli_verify.py](tools/cgir/cli_verify.py)

Example commands:
```bash
# Validate against IR schema
python tools/cgir/cli_validate.py --schema docs/ir/ir-schema.json --input examples/cgir/trace_snn_mix.json

# Simulate and write outputs
python tools/cgir/cli_sim.py --input examples/cgir/trace_snn_mix.json --out build/cgir/sim/trace_snn_mix.json

# Train and write training artifacts
python tools/cgir/cli_train.py --input examples/cgir/trace_snn_mix.json --out build/cgir/train/trace_snn_mix_attrib.json

# Visualize simulation outputs
python tools/cgir/cli_viz.py --input build/cgir/sim/trace_snn_mix.json --out build/cgir/viz/trace_snn_mix_L065.png

# Verify IR/model
python tools/cgir/cli_verify.py --input examples/cgir/trace_snn_mix.json
```

References:
- IR schemas: [docs/ir/ir-schema.json](docs/ir/ir-schema.json), [docs/ir/cgir-schema.json](docs/ir/cgir-schema.json)
- Core modules: [tools/cgir/core/oklab.py](tools/cgir/core/oklab.py), [tools/cgir/core/mixing.py](tools/cgir/core/mixing.py)

## TypeScript webapp monorepo

From the webapp workspace:
```bash
cd webapp
npm ci
# Development server (Vite)
npm run -w @oklab/app dev
# Build and preview
npm run -w @oklab/app build
npm run -w @oklab/app preview -- --port=4173 --strictPort
```

Key packages and files:
- App UI: [webapp/packages/app](webapp/packages/app), entry [webapp/packages/app/src/App.tsx](webapp/packages/app/src/App.tsx)
- Core library (OKLab, mixing, numeric): [webapp/packages/core](webapp/packages/core), entry [webapp/packages/core/src/index.ts](webapp/packages/core/src/index.ts), modules [webapp/packages/core/src/oklab.ts](webapp/packages/core/src/oklab.ts), [webapp/packages/core/src/mixing.ts](webapp/packages/core/src/mixing.ts), [webapp/packages/core/src/numeric.ts](webapp/packages/core/src/numeric.ts)
- IR types/validation: [webapp/packages/ir](webapp/packages/ir), files [webapp/packages/ir/src/ir.ts](webapp/packages/ir/src/ir.ts), [webapp/packages/ir/src/validate.ts](webapp/packages/ir/src/validate.ts)
- Worker mixing: [webapp/packages/worker/src/mixWorker.ts](webapp/packages/worker/src/mixWorker.ts), app worker [webapp/packages/app/src/worker/mixWorker.ts](webapp/packages/app/src/worker/mixWorker.ts)

## Coq build with dune

Build from the Coq directory:
```bash
cd coq
dune build
```

Project files:
- Dune file: [coq/dune](coq/dune)
- Project root: [dune-project](dune-project)
- Sources: [coq/Color](coq/Color)
- Generated: [coq/Color/Generated](coq/Color/Generated)
- Extraction: [coq/Extract/ExtractCore.v](coq/Extract/ExtractCore.v)

## Integrated workflow examples

- From PDF → IR → Markdown Reports:
  - Convert PDFs to IR: 
    ```bash
    python tools/pdf2ir/pdf2ir.py --in pdf --out build/ir --schema docs/ir/ir-schema.json
    ```
  - Optionally emit reports and extract figures:
    ```bash
    python tools/pdf2ir/pdf2ir.py --in pdf --out build/ir --schema docs/ir/ir-schema.json \
      --emit-markdown --md-out docs/reports --extract-figures --img-out docs/img/reports
    ```

- Validate and visualize a trace:
  ```bash
  # Validation
  python tools/cgir/cli_validate.py --schema docs/ir/ir-schema.json --input examples/cgir/trace_snn_mix.json
  # Simulation
  python tools/cgir/cli_sim.py --input examples/cgir/trace_snn_mix.json --out build/cgir/sim/trace_snn_mix.json
  # Visualization
  python tools/cgir/cli_viz.py --input build/cgir/sim/trace_snn_mix.json --out build/cgir/viz/trace_snn_mix_L065.png
  ```

- Run the webapp demo:
  ```bash
  cd webapp
  npm ci
  npm run -w @oklab/app dev
  # build & preview for production-like testing
  npm run -w @oklab/app build
  npm run -w @oklab/app preview -- --port=4173 --strictPort
  ```

- Build proofs:
  ```bash
  cd coq
  dune build
  ```

## Troubleshooting

- Python venv activation:
  - Ensure `source .venv/bin/activate` is executed in the current shell.
- Node/npm versions:
  - Use Node 18+; clear workspace with `rm -rf node_modules` and `npm ci` if issues arise.
- Coq/dune not found:
  - Install `coq` and `dune` via your package manager; check versions.
- Broken links or images:
  - Confirm paths relative to the editing page. Use percent-encoding for spaces, e.g., `IMG_5190%202.JPG`.
- Schema validation errors:
  - Re-check your input JSON against [docs/ir/ir-schema.json](docs/ir/ir-schema.json) and refer to [docs/methods/verification-and-validation.md](docs/methods/verification-and-validation.md).

Navigation
- Back to index: [docs/README.md](docs/README.md)
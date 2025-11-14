---
title: Symbol Grounding in Color: Foundations to Advanced Implementations
description: Repository documentation index and learning pathway for color geometry, CGIR, webapp, and Coq artifacts supporting the symbol grounding problem.
tags: [index, foundations, theory, methods, implementations, advanced, reports]
source-pdf: null
last-updated: 2025-11-13
---

# Symbol Grounding in Color: Foundations to Advanced Implementations

![Project banner: color geometry exploration](img/IMG_5190%202.JPG)

> This is the top-level documentation index for the color geometry and CGIR toolkit. Follow the learning pathway below or jump to specific implementations, reports, or references.

## Table of Contents
- Learning Pathway
- Quick Start
- Implementations Overview
- Reports
- References and Meta

## Learning Pathway

- Foundations
  - Foundations Overview — [docs/foundations/overview.md](docs/foundations/overview.md)
  - Color Spaces and OKLab Basics — [docs/foundations/color-spaces.md](docs/foundations/color-spaces.md)
  - Symbol Grounding: The Basics — [docs/foundations/symbol-grounding-basics.md](docs/foundations/symbol-grounding-basics.md)
- Theory
  - Conceptual Spaces Theory — [docs/theory/conceptual-spaces.md](docs/theory/conceptual-spaces.md)
  - Color Geometry as a Grounding Space — [docs/theory/color-geometry.md](docs/theory/color-geometry.md)
  - Neurons, SNNs, and Causality — [docs/theory/neurons-and-causality.md](docs/theory/neurons-and-causality.md)
- Methods
  - CGIR: Color Geometry Intermediate Representation — [docs/methods/cgir-ir.md](docs/methods/cgir-ir.md)
  - Validation, Verification, and Proof Artifacts — [docs/methods/verification-and-validation.md](docs/methods/verification-and-validation.md)
  - OKLab Methods and Geometry — [docs/methods/oklab-methods.md](docs/methods/oklab-methods.md)
- Implementations
  - Python CGIR Tools: Overview — [docs/implementations/python/overview.md](docs/implementations/python/overview.md)
  - TypeScript Webapp Monorepo: Overview — [docs/implementations/webapp/overview.md](docs/implementations/webapp/overview.md)
  - Coq Color Geometry: Overview — [docs/implementations/coq/overview.md](docs/implementations/coq/overview.md)
- Advanced
  - Axioms and Neurosymbolic Reasoning — [docs/advanced/axioms-and-neurosymbolics.md](docs/advanced/axioms-and-neurosymbolics.md)
  - SNN Causality in Color Geometry — [docs/advanced/causality-in-snn.md](docs/advanced/causality-in-snn.md)
  - OKLab and Geometric Semantics — [docs/advanced/oklab-geometric-semantics.md](docs/advanced/oklab-geometric-semantics.md)
- Deep-dive Series
  - Index — [docs/symbol-grounding/index.md](docs/symbol-grounding/index.md)

## Quick Start

- Build and Run Guide: [docs/BUILD.md](docs/BUILD.md)
- CGIR GUI User Guide: [docs/CGIR-GUI.md](docs/CGIR-GUI.md)

Python (CGIR tools)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/cgir/requirements.txt
python tools/cgir/cli_validate.py --schema docs/ir/ir-schema.json --input examples/cgir/trace_snn_mix.json
python tools/cgir/cli_sim.py --input examples/cgir/trace_snn_mix.json --out build/cgir/sim/trace_snn_mix.json
python tools/cgir/cli_train.py --input examples/cgir/trace_snn_mix.json --out build/cgir/train/trace_snn_mix_attrib.json
python tools/cgir/cli_viz.py --input build/cgir/sim/trace_snn_mix.json --out build/cgir/viz/trace_snn_mix_L065.png
python tools/cgir/cli_verify.py --input examples/cgir/trace_snn_mix.json
```

TypeScript (webapp workspace)
```bash
cd webapp
npm ci
npm run -w @oklab/app dev
# or build and preview
npm run -w @oklab/app build
npm run -w @oklab/app preview -- --port=4173 --strictPort
```

Coq (dune)
```bash
cd coq
dune build
```

## Implementations Overview

- Python CGIR tools (CLIs and core):
  - [tools/cgir/cli_validate.py](tools/cgir/cli_validate.py)
  - [tools/cgir/cli_sim.py](tools/cgir/cli_sim.py)
  - [tools/cgir/cli_train.py](tools/cgir/cli_train.py)
  - [tools/cgir/cli_viz.py](tools/cgir/cli_viz.py)
  - [tools/cgir/cli_verify.py](tools/cgir/cli_verify.py)
  - Core modules: [tools/cgir/core/oklab.py](tools/cgir/core/oklab.py), [tools/cgir/core/mixing.py](tools/cgir/core/mixing.py)

- TypeScript webapp monorepo:
  - App entry: [webapp/packages/app/src/App.tsx](webapp/packages/app/src/App.tsx)
  - Core lib: [webapp/packages/core/src/index.ts](webapp/packages/core/src/index.ts), [webapp/packages/core/src/oklab.ts](webapp/packages/core/src/oklab.ts)
  - Worker: [webapp/packages/worker/src/mixWorker.ts](webapp/packages/worker/src/mixWorker.ts)

- Coq sources:
  - Project: [coq/Color](coq/Color)
  - Generated: [coq/Color/Generated](coq/Color/Generated)
  - Extraction: [coq/Extract/ExtractCore.v](coq/Extract/ExtractCore.v)

## Reports

Converted report pages (targets):
- [docs/reports/color-axioms-neurosymbolic-from-color-geometry.md](docs/reports/color-axioms-neurosymbolic-from-color-geometry.md)
- [docs/reports/color-generalizing-conceptual-spaces-theory.md](docs/reports/color-generalizing-conceptual-spaces-theory.md)
- [docs/reports/color-geometry-for-snn-causality.md](docs/reports/color-geometry-for-snn-causality.md)
- [docs/reports/color-geometry-for-symbol-grounding.md](docs/reports/color-geometry-for-symbol-grounding.md)
- [docs/reports/color-oklab-web-app-geometric-semantics.md](docs/reports/color-oklab-web-app-geometric-semantics.md)

Existing report:
- [docs/reports/Color-Geometry-and-CGIR-Toolkit-Project-Report.md](docs/reports/Color-Geometry-and-CGIR-Toolkit-Project-Report.md)

## References and Meta

- Glossary — [docs/GLOSSARY.md](docs/GLOSSARY.md)
- Contributing — [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
- Navigation rules — [docs/NAVIGATION.md](docs/NAVIGATION.md)
- Style guide — [docs/STYLE.md](docs/STYLE.md)
- References — [docs/REFERENCES.md](docs/REFERENCES.md)

---

Navigation
- Next: Foundations Overview → [docs/foundations/overview.md](docs/foundations/overview.md)

Implementation notes:
- Image paths are relative to this file; banner source contains a space and is percent-encoded as IMG_5190%202.JPG.
- All links are repository-relative and will resolve when corresponding pages are added in subsequent steps.

Completion signal:
After writing docs/README.md, use attempt_completion to report success and include the path of the created file.
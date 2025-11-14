---
title: The CGIR Pipeline
description: From PDFs to IR, through Python tooling, into proof artifacts and the webapp.
tags: [deep-dive, cgir, pipeline]
source-pdf: null
last-updated: 2025-11-13
---
# The CGIR Pipeline

Trace the full pathway from source documents to IR, code, proof artifacts, and interactive demos.

## Table of Contents
- PDFs → IR schema
- Python tooling
- Coq proofs and verification
- Webapp demo integration

## PDFs → IR schema
Conversion path and schema references.
See schemas: [docs/ir/ir-schema.json](../ir/ir-schema.json), [docs/ir/cgir-schema.json](../ir/cgir-schema.json)
Converter: [tools/pdf2ir/pdf2ir.py](../../tools/pdf2ir/pdf2ir.py)

## Python tooling
CLI suite overview and data flow.
See: [docs/implementations/python/overview.md](../implementations/python/overview.md)

## Coq proofs and verification
From IR to generated proofs and extraction.
See: [docs/implementations/coq/generated.md](../implementations/coq/generated.md), [docs/implementations/coq/extraction.md](../implementations/coq/extraction.md)

## Webapp demo integration
Embodied interaction and visualization.
See: [docs/implementations/webapp/overview.md](../implementations/webapp/overview.md)

---
Navigation
- Prev: D2 — Color Geometry as Grounding Space → [docs/symbol-grounding/d2-color-geometry-as-grounding-space.md](./d2-color-geometry-as-grounding-space.md)
- Next: D4 — Verification and Proof Artifacts → [docs/symbol-grounding/d4-verification-and-proof-artifacts.md](./d4-verification-and-proof-artifacts.md)

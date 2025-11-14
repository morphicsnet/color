---
title: Validation, Verification, and Proof Artifacts
description: Validating IR, verifying properties, and connecting to proof artifacts.
tags: [methods, validation, verification, proof]
source-pdf: null
last-updated: 2025-11-13
---
# Validation, Verification, and Proof Artifacts

How we validate IR, verify properties, and relate to proofs.

## Table of Contents
- Schema validation and verification
- Coq proof artifacts
- Testing strategy

## Schema validation and verification
See CLIs: [tools/cgir/cli_validate.py](../../tools/cgir/cli_validate.py), [tools/cgir/cli_verify.py](../../tools/cgir/cli_verify.py)

## Coq proof artifacts
See: [coq/Color](../../coq/Color), [coq/Extract/ExtractCore.v](../../coq/Extract/ExtractCore.v)

## Testing strategy
Refs: [tests/cgir/test_schema_validation.py](../../tests/cgir/test_schema_validation.py), [webapp/tests/e2e/smoke.spec.ts](../../webapp/tests/e2e/smoke.spec.ts)

---
Navigation
- Prev: CGIR: Color Geometry Intermediate Representation → [docs/methods/cgir-ir.md](./cgir-ir.md)
- Next: OKLab Methods and Geometry → [docs/methods/oklab-methods.md](./oklab-methods.md)

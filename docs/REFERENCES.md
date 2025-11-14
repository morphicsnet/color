---
title: References
description: Consolidated references and internal cross-links for the documentation set.
tags: [meta, references, bibliography, docs]
source-pdf: null
last-updated: 2025-11-13
---
# References

This page consolidates primary sources, internal documents, schemas, tools, and artifacts referenced throughout the documentation set.

## Table of Contents
- Primary sources (PDFs and converted reports)
- Internal documents
- Schemas and tools
- Coq artifacts
- Webapp packages
- Citation notes

## Primary sources (PDFs and converted reports)

- Color Axioms: Neurosymbolic From Color Geometry
  - PDF: [pdf/Color Axioms Neurosymbolic From Color Geometry.pdf](../pdf/Color%20Axioms%20Neurosymbolic%20From%20Color%20Geometry.pdf)
  - Report: [docs/reports/color-axioms-neurosymbolic-from-color-geometry.md](./reports/color-axioms-neurosymbolic-from-color-geometry.md)
- Color: Generalizing Conceptual Spaces Theory
  - PDF: [pdf/color Generalizing Conceptual Spaces Theory.pdf](../pdf/color%20Generalizing%20Conceptual%20Spaces%20Theory.pdf)
  - Report: [docs/reports/color-generalizing-conceptual-spaces-theory.md](./reports/color-generalizing-conceptual-spaces-theory.md)
- Color Geometry for SNN Causality
  - PDF: [pdf/Color Geometry for SNN Causality.pdf](../pdf/Color%20Geometry%20for%20SNN%20Causality.pdf)
  - Report: [docs/reports/color-geometry-for-snn-causality.md](./reports/color-geometry-for-snn-causality.md)
- Color Geometry for Symbol Grounding
  - PDF: [pdf/Color Geometry for Symbol Grounding.pdf](../pdf/Color%20Geometry%20for%20Symbol%20Grounding.pdf)
  - Report: [docs/reports/color-geometry-for-symbol-grounding.md](./reports/color-geometry-for-symbol-grounding.md)
- Color OKLab Web App: Geometric Semantics
  - PDF: [pdf/color Oklab Web App: Geometric Semantics.pdf](../pdf/color%20Oklab%20Web%20App:%20Geometric%20Semantics.pdf)
  - Report: [docs/reports/color-oklab-web-app-geometric-semantics.md](./reports/color-oklab-web-app-geometric-semantics.md)
- Existing project report
  - [docs/reports/Color-Geometry-and-CGIR-Toolkit-Project-Report.md](./reports/Color-Geometry-and-CGIR-Toolkit-Project-Report.md)

## Internal documents

- Top-level index: [docs/README.md](./README.md)
- Build guide: [docs/BUILD.md](./BUILD.md)
- Navigation rules: [docs/NAVIGATION.md](./NAVIGATION.md)
- Style guide: [docs/STYLE.md](./STYLE.md)
- Glossary: [docs/GLOSSARY.md](./GLOSSARY.md)
- Contributing: [docs/CONTRIBUTING.md](./CONTRIBUTING.md)

## Schemas and tools

- IR schemas:
  - [docs/ir/ir-schema.json](./ir/ir-schema.json)
  - [docs/ir/cgir-schema.json](./ir/cgir-schema.json)
- PDF to IR/Markdown:
  - [tools/pdf2ir/pdf2ir.py](../tools/pdf2ir/pdf2ir.py)
- Docs link/image validator:
  - [tools/docs_lint/check_docs_links.py](../tools/docs_lint/check_docs_links.py)
- Python CLIs:
  - [tools/cgir/cli_validate.py](../tools/cgir/cli_validate.py)
  - [tools/cgir/cli_sim.py](../tools/cgir/cli_sim.py)
  - [tools/cgir/cli_train.py](../tools/cgir/cli_train.py)
  - [tools/cgir/cli_viz.py](../tools/cgir/cli_viz.py)
  - [tools/cgir/cli_verify.py](../tools/cgir/cli_verify.py)

## Coq artifacts

- Dune file: [coq/dune](../coq/dune)
- Sources: [coq/Color](../coq/Color)
- Generated: [coq/Color/Generated](../coq/Color/Generated)
- Extraction: [coq/Extract/ExtractCore.v](../coq/Extract/ExtractCore.v)

## Webapp packages

- App: [webapp/packages/app](../webapp/packages/app), entry [webapp/packages/app/src/App.tsx](../webapp/packages/app/src/App.tsx)
- Core: [webapp/packages/core](../webapp/packages/core), entry [webapp/packages/core/src/index.ts](../webapp/packages/core/src/index.ts)
  - Modules: [webapp/packages/core/src/oklab.ts](../webapp/packages/core/src/oklab.ts), [webapp/packages/core/src/mixing.ts](../webapp/packages/core/src/mixing.ts), [webapp/packages/core/src/numeric.ts](../webapp/packages/core/src/numeric.ts)
- IR types: [webapp/packages/ir](../webapp/packages/ir), files [webapp/packages/ir/src/ir.ts](../webapp/packages/ir/src/ir.ts), [webapp/packages/ir/src/validate.ts](../webapp/packages/ir/src/validate.ts)
- Worker: [webapp/packages/worker/src/mixWorker.ts](../webapp/packages/worker/src/mixWorker.ts)

## Citation notes

- Prefer path-based intra-repo links over raw titles when cross-referencing.
- When citing a PDF, include both the original PDF path under [pdf](../pdf) and its converted report under [docs/reports](./reports).
- Avoid external-only citations where possible; include a brief note and a local cross-link for traceability.
- Use percent-encoding for spaces and punctuation in link targets (e.g., `Color%20Geometry%20for%20SNN%20Causality.pdf`).

---

Back to index: [docs/README.md](./README.md)
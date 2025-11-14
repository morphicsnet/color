---
title: Documentation Navigation and Linking Rules
description: Path-based navigation, prev/next patterns, ToC placement, and link validation rules for the documentation set.
tags: [meta, navigation, rules, docs]
source-pdf: null
last-updated: 2025-11-13
---
# Documentation Navigation and Linking Rules

This guide defines how to link, order, and validate documentation pages in this repository. It applies across Foundations, Theory, Methods, Implementations, Advanced, Deep-Dive, and Reports.

## Table of Contents
- Path-based links
- Section ordering and prev/next chains
- Table of Contents placement
- File naming and normalization
- Images and media
- Link validation checklist

## Path-based links
- Use repository-relative, path-based links. Examples:
  - Foundations overview: [docs/foundations/overview.md](./foundations/overview.md)
  - IR schema: [docs/ir/ir-schema.json](./ir/ir-schema.json)
  - PDF source: [pdf/Color Geometry for Symbol Grounding.pdf](../pdf/Color%20Geometry%20for%20Symbol%20Grounding.pdf)
- Do not rely on site generators or absolute URLs.

## Section ordering and prev/next chains
Maintain consistent prev/next within each section:

- Foundations order:
  1) [docs/foundations/overview.md](./foundations/overview.md)
  2) [docs/foundations/color-spaces.md](./foundations/color-spaces.md)
  3) [docs/foundations/symbol-grounding-basics.md](./foundations/symbol-grounding-basics.md)

- Theory order:
  1) [docs/theory/conceptual-spaces.md](./theory/conceptual-spaces.md)
  2) [docs/theory/color-geometry.md](./theory/color-geometry.md)
  3) [docs/theory/neurons-and-causality.md](./theory/neurons-and-causality.md)

- Methods order:
  1) [docs/methods/cgir-ir.md](./methods/cgir-ir.md)
  2) [docs/methods/verification-and-validation.md](./methods/verification-and-validation.md)
  3) [docs/methods/oklab-methods.md](./methods/oklab-methods.md)

- Implementations order:
  - Python:
    1) [docs/implementations/python/overview.md](./implementations/python/overview.md)
    2) [docs/implementations/python/validate.md](./implementations/python/validate.md)
    3) [docs/implementations/python/sim.md](./implementations/python/sim.md)
    4) [docs/implementations/python/train.md](./implementations/python/train.md)
    5) [docs/implementations/python/viz.md](./implementations/python/viz.md)
    6) [docs/implementations/python/verify.md](./implementations/python/verify.md)
  - Webapp:
    1) [docs/implementations/webapp/overview.md](./implementations/webapp/overview.md)
    2) [docs/implementations/webapp/app.md](./implementations/webapp/app.md)
    3) [docs/implementations/webapp/core.md](./implementations/webapp/core.md)
    4) [docs/implementations/webapp/ir.md](./implementations/webapp/ir.md)
    5) [docs/implementations/webapp/worker.md](./implementations/webapp/worker.md)
  - Coq:
    1) [docs/implementations/coq/overview.md](./implementations/coq/overview.md)
    2) [docs/implementations/coq/generated.md](./implementations/coq/generated.md)
    3) [docs/implementations/coq/extraction.md](./implementations/coq/extraction.md)

- Advanced order:
  1) [docs/advanced/axioms-and-neurosymbolics.md](./advanced/axioms-and-neurosymbolics.md)
  2) [docs/advanced/causality-in-snn.md](./advanced/causality-in-snn.md)
  3) [docs/advanced/oklab-geometric-semantics.md](./advanced/oklab-geometric-semantics.md)

- Deep-Dive order:
  1) [docs/symbol-grounding/index.md](./symbol-grounding/index.md)
  2) [docs/symbol-grounding/d1-mapping-symbols-to-percepts.md](./symbol-grounding/d1-mapping-symbols-to-percepts.md)
  3) [docs/symbol-grounding/d2-color-geometry-as-grounding-space.md](./symbol-grounding/d2-color-geometry-as-grounding-space.md)
  4) [docs/symbol-grounding/d3-cgir-pipeline.md](./symbol-grounding/d3-cgir-pipeline.md)
  5) [docs/symbol-grounding/d4-verification-and-proof-artifacts.md](./symbol-grounding/d4-verification-and-proof-artifacts.md)
  6) [docs/symbol-grounding/d5-webapp-embodied-interaction.md](./symbol-grounding/d5-webapp-embodied-interaction.md)

- Reports: Provide index back to [docs/README.md](./README.md) and cross-links; no strict prev/next chain required.

## Table of Contents placement
- Include a “Table of Contents” heading near the top after a short intro.
- Keep section headings to H2/H3 for clarity.
- Do not auto-generate anchor links that depend on external tooling.

## File naming and normalization
- Use kebab-case for new Markdown documents (e.g., color-geometry-for-symbol-grounding.md).
- Reports derived from PDFs should use kebab-case of PDF stems.
- Avoid spaces in filenames.

## Images and media
- Prefer images in [docs/img](./img).
- From pages under docs/*, reference images relatively. Examples:
  - From docs/reports/* → ../img/...
  - From docs/methods/* → ../img/...
- Percent-encode spaces in existing filenames (e.g., IMG_5190%202.JPG).
- Provide alt text for accessibility and clarity.

## Link validation checklist
- All links are repository-relative and resolve to existing files.
- Prev/Next chains are complete and correct.
- Image paths are correct for the page depth.
- Cross-links follow the learning pathway: Foundations → Theory → Methods → Implementations → Advanced; Deep-Dive and Reports link across appropriately.

---
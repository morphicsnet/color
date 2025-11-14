---
title: Style and Formatting Conventions
description: Front-matter, headings, code blocks, images, tags, and writing style conventions for the docs.
tags: [meta, style, formatting, docs]
source-pdf: null
last-updated: 2025-11-13
---
# Style and Formatting Conventions

Standards for writing and organizing content to ensure a cohesive documentation set.

## Table of Contents
- Front-matter
- Headings and structure
- Code blocks and language hints
- Images and captions
- Tags and vocabulary
- Writing style

## Front-matter
Include at the top of each page:
```
---
title: <Page Title>
description: <One-line summary>
tags: [<section>, <topic>]
source-pdf: <relative path or null>
last-updated: YYYY-MM-DD
---
```
- Use ISO local date for last-updated.

## Headings and structure
- One H1 per page, matching the title.
- Use H2/H3 for sections and subsections.
- Add a “Table of Contents” heading after a short intro.
- Keep headings in sentence case.

## Code blocks and language hints
- Use explicit language fences: bash, python, ts, json.
- Reference real paths in this repo where possible:
  - IR schema: [docs/ir/ir-schema.json](./ir/ir-schema.json)
  - Python CLI: [tools/cgir/cli_validate.py](../tools/cgir/cli_validate.py)
  - App entry: [webapp/packages/app/src/App.tsx](../webapp/packages/app/src/App.tsx)

## Images and captions
- Store images under [docs/img](./img).
- Provide alt text; keep captions brief and informative.
- Encode spaces in file names (e.g., IMG_5193%202.JPG).

## Tags and vocabulary
- Controlled tags include: foundations, theory, methods, implementations, advanced, deep-dive, reports, python, typescript, coq, oklab, cgir, verification, snn, causality, axioms, neurosymbolic, conceptual-spaces, semantics, webapp.
- Add more only when necessary and consistently.

## Writing style
- Be concise, accurate, and reproducible.
- Prefer path-based intra-repo references over prose descriptions.
- Use lists and tables for clarity where appropriate.

---
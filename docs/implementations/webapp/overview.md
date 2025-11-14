---
title: TypeScript Webapp Monorepo: Overview
description: Overview of the @oklab monorepo packages and usage.
tags: [implementations, typescript, webapp]
source-pdf: null
last-updated: 2025-11-13
---
# TypeScript Webapp Monorepo: Overview

A guide to the app, core, IR, and worker packages.

## Table of Contents
- Workspace layout
- Install, build, dev

## Workspace layout
Packages:
- [webapp/packages/app](../../../webapp/packages/app)
- [webapp/packages/core](../../../webapp/packages/core)
- [webapp/packages/ir](../../../webapp/packages/ir)
- [webapp/packages/worker](../../../webapp/packages/worker)

## Install, build, dev
```bash
cd webapp
npm ci
npm run -w @oklab/app dev
```

---
Navigation
- Prev: (none)
- Next: @oklab/app: UI and Interaction → [docs/implementations/webapp/app.md](./app.md)

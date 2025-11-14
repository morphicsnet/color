---
title: Contributing Guidelines
description: How to propose changes, add pages, validate links, and keep docs consistent.
tags: [meta, contributing, guidelines]
source-pdf: null
last-updated: 2025-11-13
---
# Contributing Guidelines

This guide explains how to add or update documentation and keep it consistent and navigable.

## Table of Contents
- Proposing changes
- Adding pages and images
- Navigation and linking
- Validation checklist

## Proposing changes
- Use feature branches and pull requests.
- Reference affected pages with repository paths.

## Adding pages and images
- Place new docs under the appropriate section in [docs](./).
- Use kebab-case filenames for Markdown pages.
- Store images under [docs/img](./img) and provide alt text.

## Navigation and linking
- Follow [docs/NAVIGATION.md](./NAVIGATION.md) for ordering and prev/next chains.
- Add ToC and consistent headings per [docs/STYLE.md](./STYLE.md).

## Validation checklist
- Links resolve locally (files exist).
- Prev/Next chains are correct within the section.
- Images render from correct relative paths.
- Front-matter includes accurate tags and last-updated.

---
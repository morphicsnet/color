---
title: Training CLI
description: Configure datasets and run training routines for models over CGIR inputs.
tags: [implementations, python, training]
source-pdf: null
last-updated: 2025-11-13
---
# Training CLI

Train models and analyze outputs.

## Table of Contents
- Datasets and config
- Example training run

## Datasets and config
Describe expected input structure.

## Example training run
```bash
python tools/cgir/cli_train.py --input examples/cgir/trace_snn_mix.json --out build/cgir/train/trace_snn_mix_attrib.json
```
Sample output: [build/cgir/train/trace_snn_mix_attrib.json](../../../build/cgir/train/trace_snn_mix_attrib.json)

---
Navigation
- Prev: Simulation CLI → [docs/implementations/python/sim.md](./sim.md)
- Next: Visualization CLI → [docs/implementations/python/viz.md](./viz.md)

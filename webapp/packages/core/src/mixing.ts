import { quantize } from "./numeric";
import type { MixInput, OKLab } from "./types";

/**
 * Deterministically normalize nonnegative weights to sum to 1.0 with stable sort
 * by id then original order, matching
 * [tools/cgir/core/mixing.py: normalize_weights()](tools/cgir/core/mixing.py:16).
 */
export function normalizeWeights(inputs: MixInput[], dp = 12): MixInput[] {
  const enumerated = inputs.map((it, idx) => ({
    idx,
    item: { ...it, weight: Math.max(0, it.weight) },
  }));
  // stable sort by (id, idx)
  const sorted = [...enumerated].sort((a, b) => {
    const idCmp = a.item.id.localeCompare(b.item.id);
    return idCmp !== 0 ? idCmp : a.idx - b.idx;
  });
  const weights = sorted.map(({ item }) => item.weight);
  const sum = weights.reduce((s, w) => s + w, 0);
  const denom = sum > 0 ? sum : 1; // avoid div by zero; keep zeros
  return sorted.map(({ item }) => ({
    ...item,
    weight: quantize(item.weight / denom, dp),
  }));
}

/**
 * Convex mix in OKLab using normalized weights,
 * mirroring [tools/cgir/core/mixing.py: mix_oklab()](tools/cgir/core/mixing.py:37).
 */
export function mixOKLab(inputs: MixInput[], dp = 12): OKLab {
  const normed = normalizeWeights(inputs, dp);
  let L = 0, a = 0, b = 0;
  for (const i of normed) {
    L += i.weight * i.color.L;
    a += i.weight * i.color.a;
    b += i.weight * i.color.b;
  }
  return { L: quantize(L, dp), a: quantize(a, dp), b: quantize(b, dp) };
}

import { describe, it, expect } from "vitest";
import { normalizeWeights, mixOKLab } from "../src/mixing";
import type { MixInput, OKLab } from "../src/types";

describe("mixing.normalizeWeights", () => {
  it("clamps negatives to 0, normalizes to 1, and sorts stably by id then index", () => {
    const zero: OKLab = { L: 0, a: 0, b: 0 };
    const inputs: MixInput[] = [
      { id: "b", weight: 0.3, color: zero },
      { id: "a", weight: -1, color: zero },
      { id: "a", weight: 0.7, color: zero }
    ];
    const normed = normalizeWeights(inputs, 12);
    // Order should be: a (idx 1), a (idx 2), b (idx 0)
    expect(normed.map(i => i.id)).toEqual(["a", "a", "b"]);
    const sum = normed.reduce((s, i) => s + i.weight, 0);
    expect(sum).toBeCloseTo(1, 12);
    expect(normed.every(i => i.weight >= 0)).toBe(true);
  });
});

describe("mixing.mixOKLab", () => {
  it("produces convex combination and quantizes result", () => {
    const c1: OKLab = { L: 0.4, a: 0.1, b: 0.2 };
    const c2: OKLab = { L: 0.8, a: -0.1, b: -0.2 };
    const out = mixOKLab(
      [
        { id: "x", color: c1, weight: 2 },
        { id: "y", color: c2, weight: 1 }
      ],
      12
    );
    // Expected L = (2/3)*0.4 + (1/3)*0.8 = 0.533333...
    expect(out.L).toBeCloseTo(0.533333333333, 9);
  });
});

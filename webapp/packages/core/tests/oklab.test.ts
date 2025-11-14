import { describe, it, expect } from "vitest";
import { toOKLCh, fromOKLCh } from "../src/oklab";

describe("OKLab <-> OKLCh", () => {
  it("toOKLCh handles C≈0 by setting h=0", () => {
    const lch = toOKLCh({ L: 0.5, a: 0, b: 0 }, 12);
    expect(lch.C).toBe(0);
    expect(lch.h).toBe(0);
  });

  it("fromOKLCh(toOKLCh(ok)) ≈ ok within quantization tolerance", () => {
    const ok = { L: 0.6, a: 0.1, b: -0.2 };
    const back = fromOKLCh(toOKLCh(ok, 12), 12);
    expect(back.L).toBeCloseTo(ok.L, 10);
    expect(back.a).toBeCloseTo(ok.a, 10);
    expect(back.b).toBeCloseTo(ok.b, 10);
  });
});

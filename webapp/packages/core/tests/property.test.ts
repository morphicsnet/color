import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { clampAnglePi } from "../src/numeric";
import { toOKLCh, fromOKLCh } from "../src/oklab";

describe("property tests", () => {
  it("clampAnglePi is idempotent", () => {
    fc.assert(
      fc.property(
        fc.double({ noNaN: true, noDefaultInfinity: true, min: -1e6, max: 1e6 }),
        (h) => {
          const c1 = clampAnglePi(h);
          const c2 = clampAnglePi(c1);
          expect(Math.abs(c1 - c2)).toBeLessThanOrEqual(1e-12);
        }
      ),
      { numRuns: 100 }
    );
  });

  it("fromOKLCh(toOKLCh(ok)) ≈ ok within small tolerance (dp=12)", () => {
    fc.assert(
      fc.property(
        fc.record({
          L: fc.double({ min: 0, max: 1, noNaN: true }),
          a: fc.double({ min: -0.5, max: 0.5, noNaN: true }),
          b: fc.double({ min: -0.5, max: 0.5, noNaN: true })
        }),
        (ok) => {
          const back = fromOKLCh(toOKLCh(ok, 12), 12);
          expect(back.L).toBeCloseTo(ok.L, 9);
          expect(back.a).toBeCloseTo(ok.a, 9);
          expect(back.b).toBeCloseTo(ok.b, 9);
        }
      ),
      { numRuns: 50 }
    );
  });
});

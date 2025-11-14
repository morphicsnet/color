import { describe, it, expect } from "vitest";
import { quantize, clampAnglePi } from "../src/numeric";

describe("numeric.quantize (half-even)", () => {
  it("handles typical half-even ties", () => {
    expect(quantize(1.005, 2)).toBe(1.0);   // 100.5 -> 100 (even)
    expect(quantize(1.015, 2)).toBe(1.02);  // 101.5 -> 102 (even)
    expect(quantize(2.5, 0)).toBe(2);       // 2.5 -> 2
    expect(quantize(3.5, 0)).toBe(4);       // 3.5 -> 4
    expect(quantize(-2.5, 0)).toBe(-2);     // -2.5 -> -2
    expect(quantize(0.125, 2)).toBe(0.12);  // 12.5 -> 12
  });
});

describe("numeric.clampAnglePi", () => {
  const eps = 1e-12;
  it("wraps canonical interval [-pi, pi) and maps +pi to -pi", () => {
    expect(clampAnglePi(Math.PI)).toBe(-Math.PI);
    expect(clampAnglePi(3 * Math.PI)).toBe(-Math.PI);
  });
  it("wraps arbitrary angles", () => {
    const v = clampAnglePi(2.5 * Math.PI);
    expect(Math.abs(v - (Math.PI / 2))).toBeLessThanOrEqual(eps);
  });
});

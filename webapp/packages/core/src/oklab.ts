import { qtuple, quantize, clampAnglePi } from "./numeric";
import type { OKLab, OKLCh } from "./types";

/**
 * OKLab -> OKLCh with canonical hue wrapping and quantization,
 * per [tools/cgir/core/oklab.py: to_lch()](tools/cgir/core/oklab.py:9).
 */
export function toOKLCh(ok: OKLab, dp = 12): OKLCh {
  const { L, a, b } = ok;
  const C = Math.hypot(a, b);
  const h = C === 0 ? 0 : clampAnglePi(Math.atan2(b, a));
  return { L: quantize(L, dp), C: quantize(C, dp), h: quantize(h, dp) };
}

/**
 * OKLCh -> OKLab using a = C cos h, b = C sin h with canonical hue wrapping,
 * per [tools/cgir/core/oklab.py: from_lch()](tools/cgir/core/oklab.py:25).
 */
export function fromOKLCh(lch: OKLCh, dp = 12): OKLab {
  const { L, C, h } = lch;
  const hc = clampAnglePi(h);
  const a = C * Math.cos(hc);
  const b = C * Math.sin(hc);
  const [Lq, aq, bq] = qtuple([L, a, b], dp);
  return { L: Lq, a: aq, b: bq };
}

/**
 * Canonicalization near the gray axis:
 * if |a| and |b| <= tol, snap to a=b=0 and quantize L, matching
 * [tools/cgir/core/oklab.py: gray_axis_bias()](tools/cgir/core/oklab.py:35).
 */
export function grayAxisBias(ok: OKLab, tol = 1e-12, dp = 12): OKLab {
  const { L, a, b } = ok;
  if (Math.abs(a) <= tol && Math.abs(b) <= tol) {
    return { L: quantize(L, dp), a: 0, b: 0 };
  }
  const [Lq, aq, bq] = qtuple([L, a, b], dp);
  return { L: Lq, a: aq, b: bq };
}

/**
 * Deterministic quantization with round-half-to-even parity (banker's rounding),
 * aligned with Python reference [tools/cgir/core/numeric.py: quantize()](tools/cgir/core/numeric.py:9).
 */
function roundHalfEvenInt(x: number): number {
  if (!Number.isFinite(x)) return x;
  const s = x < 0 ? -1 : 1;
  const ax = Math.abs(x);
  const f = Math.floor(ax);
  const frac = ax - f;
  const EPS = 1e-12;
  let n: number;
  if (frac < 0.5 - EPS) n = f;
  else if (frac > 0.5 + EPS) n = f + 1;
  else n = (f % 2 === 0) ? f : f + 1; // tie -> nearest even
  return s * n;
}

export function quantize(x: number, dp = 12): number {
  const factor = Math.pow(10, dp);
  const y = x * factor;
  const r = roundHalfEvenInt(y);
  return r / factor;
}

export function qtuple(vals: number[], dp = 12): number[] {
  return vals.map((v) => quantize(v, dp));
}

export function approxEqual(x: number, y: number, tol = 1e-9): boolean {
  return Math.abs(x - y) <= tol;
}

/**
 * IEEE-754 style remainder using half-even on the quotient to mirror Python's math.remainder,
 * then canonicalization to [-pi, pi) as in
 * [tools/cgir/core/numeric.py: clamp_angle_pi()](tools/cgir/core/numeric.py:29).
 */
function ieeeRemainder(x: number, y: number): number {
  // x - y * roundHalfEven(x / y)
  return x - y * roundHalfEvenInt(x / y);
}

export function clampAnglePi(h: number): number {
  const twoPi = 2 * Math.PI;
  let wrapped = ieeeRemainder(h, twoPi); // in (-pi, pi]
  if (approxEqual(wrapped, Math.PI, 1e-15) || wrapped > Math.PI) {
    wrapped = -Math.PI;
  }
  if (wrapped < -Math.PI) wrapped += twoPi;
  if (wrapped >= Math.PI) wrapped -= twoPi;
  return wrapped;
}

export function safeDiv(a: number, b: number, defaultVal = 0): number {
  return b !== 0 ? a / b : defaultVal;
}

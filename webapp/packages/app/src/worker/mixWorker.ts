/* Web Worker for optional heavy computations (sampling, mixing).
 * Messages:
 *  - { type: "sample-ab-grid", payload: { grid: number, range: number } }
 *    -> responds { type: "sample-ab-grid-result", payload: { grid: number, a: ArrayBuffer, b: ArrayBuffer } }
 */
self.onmessage = (ev: MessageEvent) => {
  const data = ev.data as any;
  if (!data || typeof data !== "object") return;
  const { type, payload } = data;

  if (type === "sample-ab-grid") {
    const grid: number = Math.max(2, Number(payload?.grid ?? 48));
    const range: number = Number(payload?.range ?? 0.4);
    const n = grid * grid;
    const aArr = new Float32Array(n);
    const bArr = new Float32Array(n);

    let k = 0;
    for (let iy = 0; iy < grid; iy++) {
      for (let ix = 0; ix < grid; ix++) {
        const a = -range + (ix / (grid - 1)) * (2 * range);
        const b = range - (iy / (grid - 1)) * (2 * range);
        aArr[k] = a;
        bArr[k] = b;
        k++;
      }
    }

    // Transfer buffers to avoid copy
    (self as any).postMessage(
      { type: "sample-ab-grid-result", payload: { grid, a: aArr.buffer, b: bArr.buffer } },
      [aArr.buffer, bArr.buffer]
    );
    return;
  }

  // Fallback echo for debugging
  (self as any).postMessage({ type: "echo", payload });
};
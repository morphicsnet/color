import React, { useEffect, useRef, useState } from "react";

type Props = { cssOk: boolean };

export function CanvasSlice({ cssOk }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const [L, setL] = useState(0.6);
  const [grid, setGrid] = useState(48); // resolution per axis
  const size = 320;
  const range = 0.4; // visualize a,b in [-0.4, 0.4]
  const offloadThreshold = 8000; // cells count where we prefer worker

  // Init worker once
  useEffect(() => {
    try {
      workerRef.current = new Worker(
        new URL("../worker/mixWorker.ts", import.meta.url),
        { type: "module" }
      );
    } catch {
      // ignore; run single-threaded if bundler cannot resolve worker
      workerRef.current = null;
    }
    return () => {
      workerRef.current?.terminate();
      workerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const ctx = el.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, size, size);

    if (!cssOk) {
      // Draw checker to indicate unsupported rendering
      ctx.fillStyle = "#eee";
      ctx.fillRect(0, 0, size, size);
      ctx.fillStyle = "#ccc";
      for (let y = 0; y < size; y += 16) {
        for (let x = (y / 16) % 2 === 0 ? 0 : 16; x < size; x += 32) {
          ctx.fillRect(x, y, 16, 16);
        }
      }
      return;
    }

    const cellsPerAxis = grid;
    const totalCells = cellsPerAxis * cellsPerAxis;
    const cell = size / cellsPerAxis;

    const draw = (arrA: Float32Array | null, arrB: Float32Array | null) => {
      let k = 0;
      for (let iy = 0; iy < cellsPerAxis; iy++) {
        for (let ix = 0; ix < cellsPerAxis; ix++) {
          const a = arrA ? arrA[k] : -range + (ix / (cellsPerAxis - 1)) * (2 * range);
          const b = arrB ? arrB[k] : range - (iy / (cellsPerAxis - 1)) * (2 * range);
          k++;
          ctx.fillStyle = `oklab(${L} ${a} ${b})`;
          ctx.fillRect(Math.floor(ix * cell), Math.floor(iy * cell), Math.ceil(cell), Math.ceil(cell));
        }
      }
    };

    if (totalCells >= offloadThreshold && workerRef.current) {
      const onMsg = (e: MessageEvent) => {
        const { type, payload } = (e.data ?? {}) as any;
        if (type === "sample-ab-grid-result" && payload?.grid === grid) {
          const a = new Float32Array(payload.a);
          const b = new Float32Array(payload.b);
          draw(a, b);
          workerRef.current?.removeEventListener("message", onMsg);
        }
      };
      workerRef.current.addEventListener("message", onMsg);
      workerRef.current.postMessage({ type: "sample-ab-grid", payload: { grid, range } });
      return () => {
        workerRef.current?.removeEventListener("message", onMsg);
      };
    } else {
      // Main-thread sampling for smaller grids
      draw(null, null);
    }
  }, [L, grid, cssOk]);

  return (
    <section style={{ border: "1px solid #ccc", padding: 12, borderRadius: 8 }}>
      <h2>Visualize: a–b slice (fixed L)</h2>
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <label>
          L
          <input
            type="range"
            min={0}
            max={1}
            step={0.001}
            value={L}
            onChange={(e) => setL(Number(e.target.value))}
            style={{ marginLeft: 8, width: 240 }}
            aria-label="slice-L"
          />
          <span style={{ marginLeft: 8 }}>{L}</span>
        </label>
        <label>
          grid
          <input
            type="range"
            min={12}
            max={128}
            step={2}
            value={grid}
            onChange={(e) => setGrid(Number(e.target.value))}
            style={{ marginLeft: 8, width: 240 }}
            aria-label="slice-grid"
          />
          <span style={{ marginLeft: 8 }}>{grid}×{grid}</span>
        </label>
      </div>
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        style={{ marginTop: 8, border: "1px solid #999", borderRadius: 6 }}
        aria-label="a–b canvas slice"
      />
    </section>
  );
}

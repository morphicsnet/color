import React, { useMemo, useState } from "react";
import { quantize } from "../../../core/src/numeric";

type Props = { cssOk: boolean };

export function ColorPicker({ cssOk }: Props) {
  const [L, setL] = useState(0.5);
  const [a, setA] = useState(0);
  const [b, setB] = useState(0);

  const swatch = useMemo(() => `oklab(${L} ${a} ${b})`, [L, a, b]);

  return (
    <section style={{ border: "1px solid #ccc", padding: 12, borderRadius: 8 }}>
      <h2>OKLab Playground</h2>
      {!cssOk && (
        <div style={{ color: "#b26a00", marginBottom: 8 }}>
          CSS oklab()/oklch() not supported by this browser. Values shown, swatch grayed.
        </div>
      )}
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <label>
          L
          <input
            type="number"
            step="0.001"
            min={0}
            max={1}
            value={L}
            onChange={(e) => setL(Number(e.target.value))}
            style={{ marginLeft: 6, width: 120 }}
            aria-label="OKLab L"
          />
        </label>
        <label>
          a
          <input
            type="number"
            step="0.001"
            value={a}
            onChange={(e) => setA(Number(e.target.value))}
            style={{ marginLeft: 6, width: 120 }}
            aria-label="OKLab a"
          />
        </label>
        <label>
          b
          <input
            type="number"
            step="0.001"
            value={b}
            onChange={(e) => setB(Number(e.target.value))}
            style={{ marginLeft: 6, width: 120 }}
            aria-label="OKLab b"
          />
        </label>
        <div
          aria-label="OKLab swatch"
          title={swatch}
          style={{
            width: 120,
            height: 60,
            border: "1px solid #666",
            background: cssOk ? swatch : "#ccc",
          }}
        />
      </div>
      <code style={{ display: "block", marginTop: 8 }}>
        oklab({quantize(L, 12)} {quantize(a, 12)} {quantize(b, 12)})
      </code>
    </section>
  );
}

import React, { useMemo, useState } from "react";
import { clampAnglePi, quantize } from "../../../core/src/numeric";

type Props = { cssOk: boolean };

export function OKLChControls({ cssOk }: Props) {
  const [L, setL] = useState(0.6);
  const [C, setC] = useState(0.1);
  const [h, setH] = useState(0); // radians, canonicalized to [-pi, pi)

  const onHue = (val: number) => setH(clampAnglePi(val));

  const hueDeg = (h * 180) / Math.PI;
  const swatch = useMemo(() => `oklch(${L} ${C} ${hueDeg}deg)`, [L, C, hueDeg]);
  const graySnap = C <= 1e-6;

  return (
    <section style={{ border: "1px solid #ccc", padding: 12, borderRadius: 8 }}>
      <h2>OKLCh Controls</h2>
      {!cssOk && (
        <div style={{ color: "#b26a00", marginBottom: 8 }}>
          CSS oklch() not supported; swatch grayed. Controls still interactive.
        </div>
      )}
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <label style={{ width: 260 }}>
          L
          <input
            type="range"
            min={0}
            max={1}
            step={0.001}
            value={L}
            onChange={(e) => setL(Number(e.target.value))}
            style={{ width: 180, marginLeft: 8 }}
            aria-label="OKLCh L"
          />
          <span style={{ marginLeft: 8 }}>{quantize(L, 12)}</span>
        </label>
        <label style={{ width: 260 }}>
          C
          <input
            type="range"
            min={0}
            max={0.5}
            step={0.001}
            value={C}
            onChange={(e) => setC(Number(e.target.value))}
            style={{ width: 180, marginLeft: 8 }}
            aria-label="OKLCh C"
          />
          <span style={{ marginLeft: 8 }}>{quantize(C, 12)}</span>
        </label>
        <label style={{ width: 260 }}>
          h (rad)
          <input
            type="range"
            min={-Math.PI}
            max={Math.PI}
            step={0.01}
            value={h}
            onChange={(e) => onHue(Number(e.target.value))}
            style={{ width: 180, marginLeft: 8 }}
            aria-label="OKLCh h"
          />
          <span style={{ marginLeft: 8 }}>{quantize(h, 12)} rad</span>
        </label>
        <div
          aria-label="OKLCh swatch"
          title={swatch}
          style={{
            width: 120,
            height: 60,
            border: "1px solid #666",
            background: cssOk ? swatch : "#ccc",
          }}
        />
      </div>
      {graySnap && (
        <div style={{ marginTop: 8, color: "#555" }}>
          Gray-axis snapping: C≈0 ⇒ hue undefined; canonical h=0 used in conversions.
        </div>
      )}
      <code style={{ display: "block", marginTop: 8 }}>
        oklch({quantize(L, 12)} {quantize(C, 12)} {quantize(hueDeg, 12)}deg)
      </code>
    </section>
  );
}

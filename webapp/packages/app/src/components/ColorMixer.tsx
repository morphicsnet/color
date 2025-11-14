import React, { useMemo, useState } from "react";
import { normalizeWeights, mixOKLab } from "../../../core/src/mixing";
import type { MixInput, OKLab } from "../../../core/src/types";
import { quantize } from "../../../core/src/numeric";

type Props = { cssOk: boolean };

type Row = MixInput;

const emptyColor: OKLab = { L: 0.5, a: 0, b: 0 };

export function ColorMixer({ cssOk }: Props) {
  const [rows, setRows] = useState<Row[]>([
    { id: "a", weight: 1, color: { L: 0.4, a: 0.1, b: 0.2 } },
    { id: "b", weight: 1, color: { L: 0.8, a: -0.1, b: -0.2 } },
  ]);

  const sumOriginal = rows.reduce((s, r) => s + Math.max(0, r.weight), 0);
  const normed = useMemo(() => normalizeWeights(rows, 12), [rows]);
  const mixed = useMemo(() => mixOKLab(rows, 12), [rows]);
  const swatch = `oklab(${mixed.L} ${mixed.a} ${mixed.b})`;

  const addRow = () =>
    setRows((rs) => [...rs, { id: `id${rs.length + 1}`, weight: 1, color: emptyColor }]);

  const removeRow = (idx: number) => setRows((rs) => rs.filter((_, i) => i !== idx));

  const updateRow = (idx: number, updater: (r: Row) => Row) =>
    setRows((rs) => rs.map((r, i) => (i === idx ? updater(r) : r)));

  return (
    <section style={{ border: "1px solid #ccc", padding: 12, borderRadius: 8 }}>
      <h2>OKLab Mixer</h2>

      {Math.abs(sumOriginal - 1) > 1e-12 && (
        <div style={{ color: "#b26a00", marginBottom: 8 }}>
          Auto-normalized weights to sum to 1. Inputs were adjusted deterministically.
        </div>
      )}

      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", minWidth: 720 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 6 }}>ID</th>
              <th style={{ textAlign: "left", padding: 6 }}>Weight</th>
              <th style={{ textAlign: "left", padding: 6 }}>L</th>
              <th style={{ textAlign: "left", padding: 6 }}>a</th>
              <th style={{ textAlign: "left", padding: 6 }}>b</th>
              <th style={{ textAlign: "left", padding: 6 }} />
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
              <tr key={`${r.id}-${idx}`}>
                <td style={{ padding: 6 }}>
                  <input
                    value={r.id}
                    onChange={(e) => updateRow(idx, (x) => ({ ...x, id: e.target.value }))}
                    style={{ width: 100 }}
                    aria-label={`row-${idx}-id`}
                  />
                </td>
                <td style={{ padding: 6 }}>
                  <input
                    type="number"
                    step="0.001"
                    value={r.weight}
                    onChange={(e) =>
                      updateRow(idx, (x) => ({ ...x, weight: Number(e.target.value) }))
                    }
                    style={{ width: 100 }}
                    aria-label={`row-${idx}-weight`}
                  />
                </td>
                <td style={{ padding: 6 }}>
                  <input
                    type="number"
                    step="0.001"
                    value={r.color.L}
                    onChange={(e) =>
                      updateRow(idx, (x) => ({ ...x, color: { ...x.color, L: Number(e.target.value) } }))
                    }
                    style={{ width: 100 }}
                    aria-label={`row-${idx}-L`}
                  />
                </td>
                <td style={{ padding: 6 }}>
                  <input
                    type="number"
                    step="0.001"
                    value={r.color.a}
                    onChange={(e) =>
                      updateRow(idx, (x) => ({ ...x, color: { ...x.color, a: Number(e.target.value) } }))
                    }
                    style={{ width: 100 }}
                    aria-label={`row-${idx}-a`}
                  />
                </td>
                <td style={{ padding: 6 }}>
                  <input
                    type="number"
                    step="0.001"
                    value={r.color.b}
                    onChange={(e) =>
                      updateRow(idx, (x) => ({ ...x, color: { ...x.color, b: Number(e.target.value) } }))
                    }
                    style={{ width: 100 }}
                    aria-label={`row-${idx}-b`}
                  />
                </td>
                <td style={{ padding: 6 }}>
                  <button onClick={() => removeRow(idx)} aria-label={`remove-row-${idx}`}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 8 }}>
        <button onClick={addRow}>Add Input</button>
      </div>

      <div style={{ marginTop: 12, display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <div>
          <strong>Normalized weights:</strong>
          <ul style={{ margin: "6px 0 0 16px" }}>
            {normed.map((n, i) => (
              <li key={`${n.id}-${i}`}>
                {n.id}: {quantize(n.weight, 12)}
              </li>
            ))}
          </ul>
        </div>
        <div
          aria-label="Mixed swatch"
          title={`oklab(${mixed.L} ${mixed.a} ${mixed.b})`}
          style={{
            width: 140,
            height: 70,
            border: "1px solid #666",
            background: cssOk ? swatch : "#ccc",
          }}
        />
        <code>oklab({mixed.L} {mixed.a} {mixed.b})</code>
      </div>
    </section>
  );
}

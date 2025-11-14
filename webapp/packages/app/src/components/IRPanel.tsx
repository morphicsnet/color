import React, { useCallback, useEffect, useMemo, useState } from "react";
import { validateIR } from "@oklab/ir";

type ValidateResult = { valid: boolean; errors?: string[] } | null;

export function IRPanel() {
  const [doc, setDoc] = useState<any | null>(null);
  const [schema, setSchema] = useState<any | null>(null);
  const [result, setResult] = useState<ValidateResult>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [status, setStatus] = useState<string>("Idle");

  // Attempt to auto-load schema from public if available (optional convenience).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/ir-schema.json", { cache: "no-store" });
        if (res.ok) {
          const s = await res.json();
          if (!cancelled) setSchema(s);
        }
      } catch {
        // ignore; user can upload schema manually
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleFile = useCallback((file: File, kind: "doc" | "schema") => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const json = JSON.parse(String(reader.result));
        if (kind === "doc") {
          setDoc(json);
          setResult(null);
          setWarnings([]);
        } else {
          setSchema(json);
          setResult(null);
        }
      } catch (e) {
        alert(`Invalid JSON selected for ${kind}.`);
      }
    };
    reader.readAsText(file);
  }, []);

  const docWarnings = useMemo(() => {
    const w: string[] = [];
    const gd = doc?.geometry_domain;
    if (gd) {
      if (Array.isArray(gd.transforms) && gd.transforms.length === 0) {
        w.push("Warning: geometry_domain.transforms is empty.");
      }
      if (Array.isArray(gd.metrics) && gd.metrics.length === 0) {
        w.push("Warning: geometry_domain.metrics is empty.");
      }
    }
    return w;
  }, [doc]);

  const doValidate = useCallback(() => {
    if (!doc) {
      setStatus("Please load an IR JSON document first.");
      return;
    }
    if (!schema) {
      setStatus("Schema not loaded. Upload schema JSON or place ir-schema.json in public/.");
      return;
    }
    setStatus("Validating...");
    const r = validateIR(doc, schema);
    setResult(r);
    setWarnings(docWarnings);
    setStatus("Validation complete.");
  }, [doc, schema, docWarnings]);

  const colorModels = doc?.geometry_domain?.color_models;

  return (
    <section style={{ border: "1px solid #ccc", padding: 12, borderRadius: 8, marginTop: 16 }}>
      <h2>IR Panel</h2>
      <p style={{ marginTop: 0 }}>
        Load and validate IR file against schema. Recommended IR:
        <code style={{ marginLeft: 6 }}>build/ir/color Oklab Web App: Geometric Semantics.json</code>. Schema is
        defined by <code>docs/ir/ir-schema.json</code>. This panel surfaces structural warnings but does not block usage.
      </p>
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <label>
          IR JSON:
          <input
            type="file"
            accept="application/json"
            onChange={(e) => e.currentTarget.files && handleFile(e.currentTarget.files[0], "doc")}
          />
        </label>
        <label>
          Schema JSON (optional if served from /ir-schema.json):
          <input
            type="file"
            accept="application/json"
            onChange={(e) => e.currentTarget.files && handleFile(e.currentTarget.files[0], "schema")}
          />
        </label>
        <button onClick={doValidate}>Validate</button>
        <span aria-live="polite">{status}</span>
      </div>

      {result && (
        <div style={{ marginTop: 12 }}>
          <strong>Validation:</strong>{" "}
          <span style={{ color: result.valid ? "green" : "crimson" }}>{result.valid ? "Valid" : "Invalid"}</span>
          {!result.valid && result.errors && result.errors.length > 0 && (
            <details style={{ marginTop: 8 }}>
              <summary>Errors ({result.errors.length})</summary>
              <ul>
                {result.errors.map((e, idx) => (
                  <li key={idx} style={{ whiteSpace: "pre-wrap" }}>
                    {e}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {warnings.length > 0 && (
        <div style={{ marginTop: 12, color: "#b26a00" }}>
          <strong>Warnings</strong>
          <ul>
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {colorModels && (
        <div style={{ marginTop: 12 }}>
          <strong>geometry_domain.color_models</strong>
          <pre
            style={{
              background: "#f7f7f7",
              padding: 8,
              overflowX: "auto",
              borderRadius: 6,
              border: "1px solid #eee",
              maxHeight: 240
            }}
          >
            {JSON.stringify(colorModels, null, 2)}
          </pre>
        </div>
      )}
    </section>
  );
}

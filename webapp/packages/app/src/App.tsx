import React, { useEffect, useState } from "react";
import { IRPanel } from "./components/IRPanel";
import { ColorPicker } from "./components/ColorPicker";
import { OKLChControls } from "./components/OKLChControls";
import { ColorMixer } from "./components/ColorMixer";
import { CanvasSlice } from "./components/CanvasSlice";

function detectCssOk(): boolean {
  try {
    // Try both OKLab and OKLCh forms; some engines require degrees for hue in oklch()
    // Examples used only for feature-detect, not color accuracy.
    const ok1 = (window as any).CSS?.supports?.("color", "oklab(0.5 0 0)") ?? false;
    const ok2 = (window as any).CSS?.supports?.("color", "oklch(0.5 0 0deg)") ?? false;
    return Boolean(ok1 || ok2);
  } catch {
    return false;
  }
}

export default function App() {
  const [cssOk, setCssOk] = useState(false);
  useEffect(() => {
    setCssOk(detectCssOk());
  }, []);

  return (
    <div style={{ padding: 16, display: "grid", gap: 16 }}>
      <header>
        <h1>OKLab Web App: Geometric Semantics</h1>
        <p style={{ marginTop: 4 }}>
          MVP playground for OKLab/OKLCh conversions, convex mixing, and IR validation.
          Rendering uses CSS Color 4 oklab()/oklch() where supported.
        </p>
        {!cssOk && (
          <div style={{ color: "#b26a00", marginTop: 6 }}>
            This browser does not support CSS oklab()/oklch() natively. Colors will be approximated
            in UI elements as grayscale placeholders. No sRGB/XYZ fallback pipeline is included in MVP.
          </div>
        )}
      </header>

      <ColorPicker cssOk={cssOk} />
      <OKLChControls cssOk={cssOk} />
      <ColorMixer cssOk={cssOk} />
      <CanvasSlice cssOk={cssOk} />
      <IRPanel />
    </div>
  );
}

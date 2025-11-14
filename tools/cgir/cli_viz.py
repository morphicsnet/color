#!/usr/bin/env python3
"""
CGIR Visualizer (MVP)

Render an OKLab droplet slice at fixed L and overlay:
- Neuron states (ok_state)
- Event mix_raw_ok and after_projection_ok points (if present)

Usage:
  python tools/cgir/cli_viz.py --in examples/cgir/trace_snn_mix.json --slice-L 0.65 --out build/cgir/viz/trace_snn_mix_L065.png
  python tools/cgir/cli_viz.py --in examples/cgir --slice-L 0.65 --out build/cgir/viz --format png --dpi 150
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

# Ensure 'cgir' package is importable when running from repo root:
from pathlib import Path as _P
_sys_tools_dir = str(_P(__file__).resolve().parents[1])
if _sys_tools_dir not in sys.path:
    sys.path.insert(0, _sys_tools_dir)

try:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as e:
    print("ERROR: matplotlib and numpy are required. Install with: pip install matplotlib numpy", file=sys.stderr)
    print(f"Import details: {e}", file=sys.stderr)
    sys.exit(2)

try:
    from cgir.core.numeric import quantize
    from cgir.core.oklab import to_lch, from_lch
    from cgir.core.droplet import cmax_ok_v1
except Exception as e:
    print("ERROR: Failed to import cgir core modules. Did you run from repo root or install the package?", file=sys.stderr)
    print(f"Import details: {e}", file=sys.stderr)
    sys.exit(2)


@dataclass
class VizReport:
    path: Path
    wrote: Path | None
    error: str | None


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _iter_json_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    if path.is_dir():
        for p in sorted(path.rglob("*.json")):
            if p.is_file():
                yield p
        return
    yield path


def _colorstate_oklab(cs: Dict[str, Any], dp: int) -> Tuple[float, float, float]:
    """
    Resolve a ColorState dict to OKLab (L,a,b), preferring ok_state, else derive from lch_state.
    """
    if "ok_state" in cs and isinstance(cs["ok_state"], dict):
        s = cs["ok_state"]
        return (quantize(s["L"], dp), quantize(s["a"], dp), quantize(s["b"], dp))
    if "lch_state" in cs and isinstance(cs["lch_state"], dict):
        s = cs["lch_state"]
        L = float(s["L"])
        h = float(s["h"])
        Sprime = float(s["Sprime"])
        return from_lch(L, h, Sprime, dp=dp)
    raise ValueError("ColorState must contain ok_state or lch_state")


def _collect_points(instance: Dict[str, Any], dp: int) -> Dict[str, List[Tuple[float, float, float]]]:
    """
    Collect points to plot from an instance:
      - neurons: list of (L,a,b)
      - mix_raw: list of (L,a,b)
      - after_proj: list of (L,a,b)
    """
    points = {"neurons": [], "mix_raw": [], "after_proj": []}
    for n in instance.get("neurons", []):
        cs = n.get("state", {})
        try:
            points["neurons"].append(_colorstate_oklab(cs, dp))
        except Exception:
            pass

    for evt in instance.get("events", []):
        m = evt.get("mix_raw_ok")
        if isinstance(m, dict):
            try:
                points["mix_raw"].append(_colorstate_oklab(m, dp))
            except Exception:
                pass
        p = evt.get("after_projection_ok")
        if isinstance(p, dict):
            try:
                points["after_proj"].append(_colorstate_oklab(p, dp))
            except Exception:
                pass
    return points


def _compute_droplet_slice(L: float, n: int = 720) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the droplet boundary at fixed L by sampling h in [-pi, pi).
    Returns arrays a(h), b(h).
    """
    hs = np.linspace(-math.pi, math.pi, num=n, endpoint=False)
    Smax = np.array([cmax_ok_v1(L, float(h)) for h in hs], dtype=float)
    a = Smax * np.cos(hs)
    b = Smax * np.sin(hs)
    return a, b


def _draw_instance(ax: plt.Axes, instance: Dict[str, Any], slice_L: float, dp: int) -> None:
    # Droplet slice boundary
    a_bnd, b_bnd = _compute_droplet_slice(slice_L, n=720)
    ax.fill(a_bnd, b_bnd, facecolor="#dde8ff", edgecolor="#6688cc", linewidth=1.0, alpha=0.6, label="Droplet slice")

    pts = _collect_points(instance, dp)
    # Filter by L slice with small tolerance, to overlay relevant points; otherwise plot all with lighter alpha
    tolL = 1e-3
    def _mask_L(points: List[Tuple[float, float, float]]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not points:
            return np.array([]), np.array([]), np.array([])
        arr = np.array(points, dtype=float)  # shape (k,3)
        return arr[:,0], arr[:,1], arr[:,2]

    Ln, an, bn = _mask_L(pts["neurons"])
    Lm, am, bm = _mask_L(pts["mix_raw"])
    Lp, ap, bp = _mask_L(pts["after_proj"])

    def _scatter_where(Larr, A, B, color, label, alpha_all=0.9):
        if Larr.size == 0: 
            return
        # Prefer showing points at the requested slice
        sel = np.where(np.abs(Larr - slice_L) <= tolL)[0]
        if sel.size > 0:
            ax.scatter(A[sel], B[sel], c=color, s=30, marker="o", edgecolors="k", linewidths=0.5, alpha=alpha_all, label=label)
        # Also lightly show off-slice points to give context
        other = np.where(np.abs(Larr - slice_L) > tolL)[0]
        if other.size > 0:
            ax.scatter(A[other], B[other], c=color, s=12, marker=".", alpha=0.3)

    _scatter_where(Ln, an, bn, "#555555", "neurons", 0.9)
    _scatter_where(Lm, am, bm, "#cc3333", "mix_raw_ok", 0.9)
    _scatter_where(Lp, ap, bp, "#33aa55", "after_projection_ok", 0.9)

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("a")
    ax.set_ylabel("b")
    ax.set_title(f"OKLab droplet slice at L={slice_L:.3f}")
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.4)
    # Legend with unique labels
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    if uniq:
        ax.legend(uniq.values(), uniq.keys(), loc="best", framealpha=0.85)


def _render_file(in_file: Path, out_path: Path, slice_L: float, dp: int, dpi: int, fmt: str) -> VizReport:
    try:
        instance = _read_json(in_file)
    except Exception as e:
        return VizReport(in_file, None, f"read error: {e}")

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(6.5, 6.5), dpi=dpi)
        _draw_instance(ax, instance, slice_L, dp)
        fig.tight_layout()
        fig.savefig(out_path, format=fmt, dpi=dpi)
        plt.close(fig)
        return VizReport(in_file, out_path, None)
    except Exception as e:
        return VizReport(in_file, None, f"render error: {e}")


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="CGIR visualizer: OKLab droplet slice")
    ap.add_argument("--in", dest="in_path", required=True, help="CGIR file or directory")
    ap.add_argument("--slice-L", dest="slice_L", type=float, required=True, help="Fixed L for the droplet slice (0..1)")
    ap.add_argument("--out", dest="out", required=True, help="Output file path (for single input) or directory (for multiple inputs)")
    ap.add_argument("--format", dest="fmt", choices=["png", "svg"], default="png", help="Image format (default: png)")
    ap.add_argument("--dpi", dest="dpi", type=int, default=160, help="DPI for raster outputs (default: 160)")
    ap.add_argument("--quantize-dp", dest="dp", type=int, default=12, help="Decimal places for rounding policy (default 12)")
    args = ap.parse_args(argv)

    in_path = Path(args.in_path)
    out_path = Path(args.out)
    if not (0.0 <= args.slice_L <= 1.0):
        print("ERROR: --slice-L must be in [0,1]", file=sys.stderr)
        return 2

    reports: List[VizReport] = []
    if in_path.is_file():
        # Single file mode
        out_file = out_path
        if out_file.is_dir():
            # If user passed a directory for a single input, derive a filename
            out_file = out_file / f"{in_path.stem}_L{args.slice_L:.3f}.{args.fmt}"
        rep = _render_file(in_path, out_file, args.slice_L, args.dp, args.dpi, args.fmt)
        reports.append(rep)
    else:
        # Directory mode: mirror filenames under out dir
        out_path.mkdir(parents=True, exist_ok=True)
        for fp in _iter_json_files(in_path):
            rel_name = fp.stem
            out_file = out_path / f"{rel_name}_L{args.slice_L:.3f}.{args.fmt}"
            rep = _render_file(fp, out_file, args.slice_L, args.dp, args.dpi, args.fmt)
            reports.append(rep)

    failed = [r for r in reports if r.error]
    for r in reports:
        status = "OK" if not r.error else "FAILED"
        print(f"- {r.path}: {status}{'' if not r.wrote else f' -> {r.wrote}'}")
        if r.error:
            print(f"    * {r.error}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
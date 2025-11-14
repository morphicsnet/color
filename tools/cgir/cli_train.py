#!/usr/bin/env python3
"""
CGIR Trainer Skeleton (MVP)

Event-driven geometric attribution using NNLS in OKLab:
- For each event, solve alphas >= 0 minimizing || A * alphas - b ||_2
  where:
    A = matrix of input OKLab vectors stacked as columns (shape 3 x N)
    b = target OKLab vector (3,)
- Then deterministically normalize alphas to sum to 1 (if sum > 0),
  else fall back to uniform distribution over inputs.
- Bias is currently fixed at 0.0 in MVP; future versions can add bias as
  an additional nonnegative variable with gray-axis vector.

Outputs:
- Writes an attribution JSON alongside each input file under --out, containing:
  - per-event "alphas": list of {source.id, alpha}
  - "residual_norm": float (||A*alpha - b||_2)
  - "sum_alpha": float (sum of alphas before normalization)
  - "normalized": bool (true if we normalized a positive sum to 1)

Usage:
  python tools/cgir/cli_train.py --in examples/cgir --out build/cgir/train
  python tools/cgir/cli_train.py --in examples/cgir/trace_snn_mix.json --out build/cgir/train --quantize-dp 12
"""

from __future__ import annotations

import argparse
import json
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
    from scipy.optimize import nnls
except Exception as e:
    print("ERROR: numpy and scipy are required. Install with: pip install numpy scipy", file=sys.stderr)
    print(f"Import details: {e}", file=sys.stderr)
    sys.exit(2)

try:
    from cgir.core.numeric import quantize
    from cgir.core.oklab import from_lch
except Exception as e:
    print("ERROR: Failed to import cgir core modules. Did you run from repo root or install the package?", file=sys.stderr)
    print(f"Import details: {e}", file=sys.stderr)
    sys.exit(2)


@dataclass
class TrainReport:
    path: Path
    wrote: Path | None
    error: str | None


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


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


def _collect_neuron_oklab(instance: Dict[str, Any], dp: int) -> Dict[str, Tuple[float, float, float]]:
    m: Dict[str, Tuple[float, float, float]] = {}
    for n in instance.get("neurons", []):
        nid = n["id"]
        cs = n.get("state", {})
        m[nid] = _colorstate_oklab(cs, dp)
    return m


def _event_target_ok(ev: Dict[str, Any], dp: int) -> Tuple[float, float, float]:
    """
    Choose attribution target vector for event:
      MVP: use 'output_state_ok' if present, else 'after_projection_ok', else 'mix_raw_ok'.
    """
    for key in ("output_state_ok", "after_projection_ok", "mix_raw_ok"):
        node = ev.get(key)
        if isinstance(node, dict):
            try:
                return _colorstate_oklab(node, dp)
            except Exception:
                pass
    raise ValueError("No target ColorState found in event (output_state_ok/after_projection_ok/mix_raw_ok)")


def _event_inputs(ev: Dict[str, Any]) -> List[str]:
    inputs = ev.get("mixing", {}).get("inputs", [])
    ids: List[str] = []
    for ent in inputs:
        try:
            ids.append(ent["source"]["id"])
        except Exception:
            pass
    if not ids:
        raise ValueError("Event has no inputs to attribute")
    return ids


def _build_matrix_A(id2ok: Dict[str, Tuple[float, float, float]], ids: List[str]) -> np.ndarray:
    """
    Build A (3 x N) columns are input OKLab vectors.
    """
    cols = []
    for nid in ids:
        L, a, b = id2ok[nid]
        cols.append([L, a, b])
    A = np.array(cols, dtype=float).T  # shape (3, N)
    return A


def _attribution_nnls(A: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Solve nnls per row? Standard nnls is for A(m x n) and b(m,) with m >= n, n >= 1.
    Here m=3 (L,a,b), n = N inputs; use nnls on flattened augmented rows.

    Approach:
      - Solve min ||A^T y - b'|| with nnls requires shape (m x n), b(m,)
      - We instead directly call nnls(A, b) which expects shape (m x n), m=3.

    Returns:
      alpha (N,), residual_norm
    """
    alpha, resnorm = nnls(A, b)
    # nnls returns residual norm as Euclidean norm of A*alpha - b
    return alpha, float(resnorm)


def _normalize_alphas(alpha: np.ndarray, dp: int) -> Tuple[np.ndarray, float, bool]:
    s = float(alpha.sum())
    if s > 0.0:
        alpha_n = alpha / s
        return np.array([quantize(float(x), dp) for x in alpha_n], dtype=float), s, True
    # Fallback: uniform
    n = alpha.shape[0]
    if n <= 0:
        return alpha, 0.0, False
    alpha_u = np.full((n,), 1.0 / n, dtype=float)
    return np.array([quantize(float(x), dp) for x in alpha_u], dtype=float), 0.0, False


def process_instance(instance: Dict[str, Any], dp: int) -> Dict[str, Any]:
    """
    Compute attributions for each event and return a compact attribution structure.
    """
    id2ok = _collect_neuron_oklab(instance, dp)
    events = instance.get("events", [])
    if not isinstance(events, list):
        return {"error": "events not a list"}

    out = {
        "cgir_version": instance.get("cgir_version", "0.1.0"),
        "attribution_version": "0.1.0",
        "file_meta": {"source_title": instance.get("title", None)},
        "events": [],
    }

    for i, ev in enumerate(events):
        try:
            target = _event_target_ok(ev, dp)
            input_ids = _event_inputs(ev)
            A = _build_matrix_A(id2ok, input_ids)  # (3, N)
            b = np.array(target, dtype=float)      # (3,)

            alpha, res = _attribution_nnls(A, b)
            alpha_n, sum_alpha, normalized = _normalize_alphas(alpha, dp)

            out["events"].append({
                "index": i,
                "target_ok": {"L": quantize(target[0], dp), "a": quantize(target[1], dp), "b": quantize(target[2], dp)},
                "inputs": [{"id": nid} for nid in input_ids],
                "alphas": [{"id": nid, "alpha": float(a)} for nid, a in zip(input_ids, alpha_n)],
                "residual_norm": float(res),
                "sum_alpha_before_norm": sum_alpha,
                "normalized": bool(normalized),
            })
        except Exception as e:
            out["events"].append({
                "index": i,
                "error": f"{e}",
            })

    return out


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="CGIR trainer skeleton (NNLS-based attribution)")
    ap.add_argument("--in", dest="in_path", required=True, help="Input CGIR file or directory")
    ap.add_argument("--out", dest="out_dir", required=True, help="Directory to write attribution JSON")
    ap.add_argument("--quantize-dp", dest="dp", type=int, default=12, help="Decimal places for rounding policy (default 12)")
    args = ap.parse_args(argv)

    in_path = Path(args.in_path)
    out_dir = Path(args.out_dir)

    reports: List[TrainReport] = []
    for fp in _iter_json_files(in_path):
        if not fp.exists():
            reports.append(TrainReport(fp, None, "path does not exist"))
            continue
        try:
            instance = _read_json(fp)
        except Exception as e:
            reports.append(TrainReport(fp, None, f"read error: {e}"))
            continue

        try:
            attrib = process_instance(instance, dp=args.dp)
        except Exception as e:
            reports.append(TrainReport(fp, None, f"training error: {e}"))
            continue

        rel = fp.name if in_path.is_file() else fp.relative_to(in_path).as_posix()
        out_path = out_dir / rel
        # Change extension or suffix to _attrib.json if it's a file
        out_path = out_path.with_name(out_path.stem + "_attrib.json")
        try:
            _write_json(out_path, attrib)
            reports.append(TrainReport(fp, out_path, None))
        except Exception as e:
            reports.append(TrainReport(fp, None, f"write error: {e}"))

    failed = [r for r in reports if r.error]
    for r in reports:
        status = "OK" if not r.error else "FAILED"
        print(f"- {r.path}: {status}{'' if not r.wrote else f' -> {r.wrote}'}")
        if r.error:
            print(f"    * {r.error}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
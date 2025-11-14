#!/usr/bin/env python3
"""
CGIR Deterministic Simulation Kernel (MVP)

- Loads CGIR JSON (file or directory), optionally validates against schema.
- For each event:
  1) Canonicalize/collect neuron OKLab states.
  2) Normalize input weights deterministically.
  3) Compute convex mix in OKLab (mix_raw_ok).
  4) Project into droplet via radial clamp (after_projection_ok).
  5) Compute reachable = inside_droplet(mix_raw_ok).
  6) Set output_state_ok = after_projection_ok.
  7) Fill canonical_alpha with normalized inputs (bias=0.0).

- Writes updated JSON to --out directory preserving relative paths.

Usage:
  python tools/cgir/cli_sim.py --in examples/cgir --out build/cgir/sim
  python tools/cgir/cli_sim.py --in examples/cgir/trace_snn_mix.json --out build/cgir/sim --quantize-dp 12
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

# Ensure 'cgir' package is importable when running from repo root:
# Add the 'tools' directory (parent of the 'cgir' package) to sys.path.
from pathlib import Path as _P
_sys_tools_dir = str(_P(__file__).resolve().parents[1])
if _sys_tools_dir not in sys.path:
    sys.path.insert(0, _sys_tools_dir)

try:
    from cgir.core.numeric import quantize, approx_equal
    from cgir.core.oklab import from_lch
    from cgir.core.droplet import project_radial_clamp, is_inside_droplet
    from cgir.core.mixing import InputWeight, normalize_weights, mix_oklab
except Exception as e:
    print("ERROR: Failed to import cgir core modules. Did you run from repo root or install the package?", file=sys.stderr)
    print(f"Import details: {e}", file=sys.stderr)
    sys.exit(2)

# Optional schema validation
try:
    import jsonschema
    from jsonschema import Draft202012Validator
    _HAS_JSONSCHEMA = True
except Exception:
    _HAS_JSONSCHEMA = False


@dataclass
class SimReport:
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


def _validate_schema_if_requested(instance: Dict[str, Any], schema_path: Path) -> List[str]:
    if not _HAS_JSONSCHEMA:
        return []
    try:
        schema = _read_json(schema_path)
        v = Draft202012Validator(schema)
        errs = [f"{list(e.path)}: {e.message}" for e in v.iter_errors(instance)]
        return errs
    except Exception as e:
        return [f"schema validation failed: {e}"]


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


def _set_state_ok(obj: Dict[str, Any], L: float, a: float, b: float, dp: int) -> None:
    obj["ok_state"] = {"L": quantize(L, dp), "a": quantize(a, dp), "b": quantize(b, dp)}
    # optional: remove lch_state if present to avoid conflicting dual representation in outputs
    if "lch_state" in obj:
        try:
            del obj["lch_state"]
        except Exception:
            pass


def _process_event(evt: Dict[str, Any], id2ok: Dict[str, Tuple[float, float, float]], dp: int) -> None:
    mixing = evt.get("mixing", {})
    inputs_spec = mixing.get("inputs", [])
    iw_list = [InputWeight(neuron_id=spec["source"]["id"], weight=float(spec["weight"])) for spec in inputs_spec]
    normed = normalize_weights(iw_list, dp=dp)

    # Convex mix in OKLab
    Lm, am, bm = mix_oklab(id2ok, normed, dp=dp)

    # Write mix_raw_ok
    mix_raw_ok = evt.get("mix_raw_ok")
    if not isinstance(mix_raw_ok, dict):
        mix_raw_ok = {}
        evt["mix_raw_ok"] = mix_raw_ok
    _set_state_ok(mix_raw_ok, Lm, am, bm, dp)

    # Projection
    Lp, ap, bp = project_radial_clamp(Lm, am, bm, dp=dp)
    after_proj = evt.get("after_projection_ok")
    if not isinstance(after_proj, dict):
        after_proj = {}
        evt["after_projection_ok"] = after_proj
    _set_state_ok(after_proj, Lp, ap, bp, dp)

    # Reachability: inside droplet for the raw mix
    inside = is_inside_droplet(Lm, am, bm, dp=dp)
    evt["reachable"] = bool(inside)

    # Canonical alphas
    can = evt.get("canonical_alpha")
    if not isinstance(can, dict):
        can = {}
        evt["canonical_alpha"] = can
    can["inputs"] = [{"source": {"id": iw.neuron_id}, "alpha": quantize(iw.weight, dp)} for iw in normed]
    # Bias handling (MVP): 0.0 unless provided; keep if user already set it
    if "bias" not in can:
        can["bias"] = 0.0

    # Output = after_projection_ok
    out_ok = evt.get("output_state_ok")
    if not isinstance(out_ok, dict):
        out_ok = {}
        evt["output_state_ok"] = out_ok
    _set_state_ok(out_ok, Lp, ap, bp, dp)


def process_instance(instance: Dict[str, Any], dp: int) -> Dict[str, Any]:
    id2ok = _collect_neuron_oklab(instance, dp)
    events = instance.get("events", [])
    if not isinstance(events, list):
        return instance
    for evt in events:
        _process_event(evt, id2ok, dp)
    return instance


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="CGIR deterministic simulator")
    ap.add_argument("--in", dest="in_path", required=True, help="Input CGIR file or directory")
    ap.add_argument("--out", dest="out_dir", required=True, help="Output directory for simulated JSON")
    ap.add_argument("--schema", dest="schema_path", default="docs/ir/cgir-schema.json", help="Schema path (optional validation)")
    ap.add_argument("--quantize-dp", dest="dp", type=int, default=12, help="Decimal places for rounding policy (default 12)")
    ap.add_argument("--validate", action="store_true", help="Validate against schema before sim")
    args = ap.parse_args(argv)

    in_path = Path(args.in_path)
    out_dir = Path(args.out_dir)
    schema_path = Path(args.schema_path)

    reports: List[SimReport] = []
    for fp in _iter_json_files(in_path):
        if not fp.exists():
            reports.append(SimReport(fp, None, "path does not exist"))
            continue

        try:
            instance = _read_json(fp)
        except Exception as e:
            reports.append(SimReport(fp, None, f"read error: {e}"))
            continue

        if args.validate:
            errs = _validate_schema_if_requested(instance, schema_path)
            if errs:
                reports.append(SimReport(fp, None, f"schema errors: {errs[:3]}{'...' if len(errs) > 3 else ''}"))
                continue

        try:
            updated = process_instance(instance, dp=args.dp)
        except Exception as e:
            reports.append(SimReport(fp, None, f"simulation error: {e}"))
            continue

        rel = fp.name if in_path.is_file() else fp.relative_to(in_path).as_posix()
        out_path = out_dir / rel
        try:
            _write_json(out_path, updated)
            reports.append(SimReport(fp, out_path, None))
        except Exception as e:
            reports.append(SimReport(fp, None, f"write error: {e}"))

    failed = [r for r in reports if r.error]
    for r in reports:
        status = "OK" if not r.error else "FAILED"
        print(f"- {r.path}: {status}{'' if not r.wrote else f' -> {r.wrote}'}")
        if r.error:
            print(f"    * {r.error}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
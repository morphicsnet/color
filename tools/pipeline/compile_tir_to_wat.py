#!/usr/bin/env python3
"""
compile_tir_to_wat.py

One-shot pipeline driver:
  T-IR (JSON) --lower/erasure--> O-IR (JSON) --optional DCE--> WAT (WebAssembly Text)

Features:
- Loads and validates T-IR against docs/ir/tir-schema.json
- Lowers to O-IR via tools.oir.lower_from_tir (includes proof-only definition erasure certificates)
- Optional DCE for O-IR via tools.oir.passes.dce
- Optional O-IR schema validation (docs/ir/oir-schema.json)
- Emits WAT using the MVP codegen in tools/pipeline/compile_oir_to_wat.py

Usage:
  python tools/pipeline/compile_tir_to_wat.py --in docs/ir/examples/minimal.json --out-wat build/wasm/minimal.wat --debug
  python tools/pipeline/compile_tir_to_wat.py --in <TIR.json> --out-wat <out.wat> --oir-out <out.oir.json> --opt 2 --dce --validate-oir --debug
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List

# Resolve repo root to ensure imports work regardless of current working dir.
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]  # tools/pipeline/ -> tools/ -> repo root
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

TIR_SCHEMA_PATH = Path("docs/ir/tir-schema.json")
OIR_SCHEMA_PATH = Path("docs/ir/oir-schema.json")

try:
    from tools.tir.codec import load_tir  # type: ignore
    from tools.oir.lower_from_tir import LowerFromTIR, LowerConfig  # type: ignore
    from tools.oir.passes.dce import run_dce  # type: ignore
    from tools.oir.passes.cse import run_cse  # type: ignore
    from tools.oir.passes.const_fold import run_const_fold  # type: ignore
    from tools.pipeline.compile_oir_to_wat import oir_to_wat  # type: ignore
except Exception as e:
    print(
        "ERROR: failed to import required modules.\n"
        f"  repo_root={_REPO_ROOT}\n"
        f"  sys.path[0]={sys.path[0]}\n"
        f"Details: {e}",
        file=sys.stderr,
    )
    sys.exit(2)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_json(doc: Any, schema_path: Path) -> List[str]:
    """Validate 'doc' against JSON Schema at 'schema_path'. Returns list of errors (empty if valid or jsonschema missing)."""
    try:
        import jsonschema  # type: ignore
        from jsonschema import Draft202012Validator  # type: ignore
    except Exception:
        return []
    if not schema_path.exists():
        return [f"schema not found: {schema_path}"]
    schema = _load_json(schema_path)
    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(doc), key=lambda e: e.path)
    msgs: List[str] = []
    for err in errors:
        loc = "$"
        if err.path:
            loc = "$." + ".".join(str(p) for p in err.path)
        msgs.append(f"{loc}: {err.message}")
    return msgs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compile T-IR JSON to WebAssembly Text (WAT) via O-IR")
    ap.add_argument("--in", dest="inp", required=True, help="Path to input T-IR JSON")
    ap.add_argument("--out-wat", dest="out_wat", required=True, help="Path to WAT output file")
    ap.add_argument("--oir-out", dest="oir_out", help="Optional: path to write intermediate O-IR JSON")
    ap.add_argument("--opt", type=int, default=2, choices=[0, 1, 2, 3], help="Lowering optimizations level (default: 2)")
    ap.add_argument("--const-fold", dest="const_fold", action="store_true", help="Run O-IR constant folding before CSE/DCE")
    ap.add_argument("--cse", action="store_true", help="Run O-IR CSE before DCE")
    ap.add_argument("--dce", action="store_true", help="Run O-IR DCE before emitting WAT")
    ap.add_argument("--validate-oir", action="store_true", help="Validate O-IR with jsonschema (if available)")
    ap.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = ap.parse_args(argv)

    tir_path = Path(args.inp)
    wat_path = Path(args.out_wat)
    oir_out_path = Path(args.oir_out) if args.oir_out else None

    # 1) Load + validate T-IR
    try:
        tir = load_tir(tir_path, validate=True, schema_path=TIR_SCHEMA_PATH)
    except Exception as e:
        print(f"[fail] T-IR load/validate error: {e}", file=sys.stderr)
        return 2

    # 2) Lower to O-IR
    cfg = LowerConfig(debug=bool(args.debug), opt_level=int(args.opt))
    lowerer = LowerFromTIR(cfg)
    try:
        oir = lowerer.lower(tir)
    except Exception as e:
        print(f"[fail] lowering error: {e}", file=sys.stderr)
        return 2

    # 2.5) Optional const-fold
    if args.const_fold:
        try:
            oir = run_const_fold(oir, debug=args.debug)
        except Exception as e:
            print(f"[fail] const-fold error: {e}", file=sys.stderr)
            return 2

    # 2.6) Optional CSE
    if args.cse:
        try:
            oir = run_cse(oir, debug=args.debug)
        except Exception as e:
            print(f"[fail] CSE error: {e}", file=sys.stderr)
            return 2

    # 2.7) Optional DCE
    if args.dce:
        try:
            oir = run_dce(oir, debug=args.debug)
        except Exception as e:
            print(f"[fail] DCE error: {e}", file=sys.stderr)
            return 2

    # 3) Optional O-IR validation
    if args.validate_oir:
        errs = _validate_json(oir, OIR_SCHEMA_PATH)
        if errs:
            print(f"[fail] O-IR schema validation: {len(errs)} error(s):", file=sys.stderr)
            for i, m in enumerate(errs, 1):
                print(f"  {i:03d}) {m}", file=sys.stderr)
            return 1

    # 4) Optionally write O-IR
    if oir_out_path:
        oir_out_path.parent.mkdir(parents=True, exist_ok=True)
        with oir_out_path.open("w", encoding="utf-8") as f:
            json.dump(oir, f, indent=2, ensure_ascii=False, sort_keys=False)
            f.write("\n")
        if args.debug:
            sys.stderr.write(f"[ok] wrote O-IR to {oir_out_path}\n")

    # 5) Emit WAT
    try:
        wat_text = oir_to_wat(oir, debug=args.debug)
    except Exception as e:
        print(f"[fail] codegen error: {e}", file=sys.stderr)
        return 2

    wat_path.parent.mkdir(parents=True, exist_ok=True)
    with wat_path.open("w", encoding="utf-8") as f:
        f.write(wat_text if wat_text.endswith("\n") else wat_text + "\n")

    if args.debug:
        sys.stderr.write(f"[ok] wrote WAT to {wat_path}\n")
    else:
        print(f"[ok] {wat_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
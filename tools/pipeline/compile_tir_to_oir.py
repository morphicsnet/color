#!/usr/bin/env python3
"""
compile_tir_to_oir.py

End-to-end driver to compile T-IR JSON to O-IR JSON.

- Loads and validates T-IR against docs/ir/tir-schema.json
- Lowers to O-IR via tools.oir.lower_from_tir
- Optional DCE pass via tools.oir.passes.dce
- Optionally validates O-IR against docs/ir/oir-schema.json
- Writes O-IR to the requested output path

Usage:
  python tools/pipeline/compile_tir_to_oir.py --in docs/ir/examples/minimal.json --out build/oir/minimal.oir.json
  python tools/pipeline/compile_tir_to_oir.py --in <TIR.json> --out <OIR.json> --opt 2 --dce --validate-oir --debug
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List

# Paths
TIR_SCHEMA_PATH = Path("docs/ir/tir-schema.json")
OIR_SCHEMA_PATH = Path("docs/ir/oir-schema.json")

# Local imports (repo-relative)
try:
    from tools.tir.codec import load_tir  # type: ignore
    from tools.oir.lower_from_tir import LowerFromTIR, LowerConfig  # type: ignore
    from tools.oir.passes.dce import run_dce  # type: ignore
    from tools.oir.passes.cse import run_cse  # type: ignore
    from tools.oir.passes.const_fold import run_const_fold  # type: ignore
except Exception as e:
    print(
        "ERROR: failed to import required modules. "
        "Run this from the repository root so 'tools' is on the module path.\n"
        f"Details: {e}",
        file=sys.stderr,
    )
    sys.exit(2)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_json(doc: Any, schema_path: Path) -> List[str]:
    """Validate 'doc' against JSON Schema at 'schema_path'. Returns list of errors."""
    try:
        import jsonschema  # type: ignore
        from jsonschema import Draft202012Validator  # type: ignore
    except Exception:
        # jsonschema not installed; skip validation
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
    ap = argparse.ArgumentParser(description="Compile T-IR JSON to O-IR JSON")
    ap.add_argument("--in", dest="inp", required=True, help="Path to input T-IR JSON")
    ap.add_argument("--out", dest="out", required=True, help="Path to output O-IR JSON")
    ap.add_argument("--opt", type=int, default=2, choices=[0, 1, 2, 3], help="Optimization level (default: 2)")
    ap.add_argument("--debug", action="store_true", help="Enable debug logs")
    ap.add_argument("--validate-oir", action="store_true", help="Validate O-IR output with jsonschema (if available)")
    ap.add_argument("--const-fold", dest="const_fold", action="store_true", help="Run O-IR constant folding before CSE/DCE")
    ap.add_argument("--cse", action="store_true", help="Run O-IR CSE pass before DCE")
    ap.add_argument("--dce", action="store_true", help="Run O-IR DCE pass before writing")
    args = ap.parse_args(argv)

    tir_path = Path(args.inp)
    out_path = Path(args.out)

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

    # 2.5) Optional const-fold pass
    if args.const_fold:
        try:
            oir = run_const_fold(oir, debug=args.debug)
        except Exception as e:
            print(f"[fail] const-fold error: {e}", file=sys.stderr)
            return 2

    # 2.6) Optional CSE pass
    if args.cse:
        try:
            oir = run_cse(oir, debug=args.debug)
        except Exception as e:
            print(f"[fail] CSE error: {e}", file=sys.stderr)
            return 2

    # 2.7) Optional DCE pass
    if args.dce:
        try:
            oir = run_dce(oir, debug=args.debug)
        except Exception as e:
            print(f"[fail] DCE error: {e}", file=sys.stderr)
            return 2

    # 3) Optionally validate O-IR
    if args.validate_oir:
        errs = _validate_json(oir, OIR_SCHEMA_PATH)
        if errs:
            print(f"[fail] O-IR schema validation: {len(errs)} error(s):", file=sys.stderr)
            for i, m in enumerate(errs, 1):
                print(f"  {i:03d}) {m}", file=sys.stderr)
            return 1

    # 4) Write O-IR
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(oir, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")

    if args.debug:
        sys.stderr.write(f"[ok] wrote O-IR to {out_path}\n")
    else:
        print(f"[ok] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
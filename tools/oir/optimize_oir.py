#!/usr/bin/env python3
"""
optimize_oir.py

Apply O-IR optimization passes to an O-IR JSON module.

Supported passes (enable via flags):
- --const-fold   : Constant folding (intra-basic-block)
- --cse          : Common subexpression elimination for Consts (intra-basic-block)
- --dce          : Dead Code Elimination (dead pure bindings + unused internal functions)

Validation:
- --validate-oir : Validate input/output against docs/ir/oir-schema.json (if jsonschema installed)

Usage:
  python tools/oir/optimize_oir.py --in docs/ir/examples/oir/add_i32.json --out build/oir/add_i32.opt.json --const-fold --cse --dce --validate-oir --debug
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List

REPO_ROOT = Path(__file__).resolve().parents[2]
OIR_SCHEMA_PATH = Path("docs/ir/oir-schema.json")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def _validate_json(doc: Any, schema_path: Path) -> List[str]:
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
    sys.path.insert(0, str(REPO_ROOT))  # ensure 'tools' imports work when run from repo root

    ap = argparse.ArgumentParser(description="Optimize an O-IR JSON with selected passes")
    ap.add_argument("--in", dest="inp", required=True, help="Path to input O-IR JSON")
    ap.add_argument("--out", dest="out", required=True, help="Path to output O-IR JSON")
    ap.add_argument("--const-fold", dest="const_fold", action="store_true", help="Run constant folding")
    ap.add_argument("--cse", action="store_true", help="Run CSE")
    ap.add_argument("--dce", action="store_true", help="Run DCE")
    ap.add_argument("--validate-oir", action="store_true", help="Validate I/O with jsonschema (if available)")
    ap.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = ap.parse_args(argv)

    try:
        from tools.oir.passes.const_fold import run_const_fold  # type: ignore
        from tools.oir.passes.cse import run_cse  # type: ignore
        from tools.oir.passes.dce import run_dce  # type: ignore
    except Exception as e:
        print(f"[fail] import error: {e}", file=sys.stderr)
        return 2

    in_path = Path(args.inp)
    out_path = Path(args.out)

    try:
        oir = _load_json(in_path)
    except Exception as e:
        print(f"[fail] failed to read O-IR: {e}", file=sys.stderr)
        return 2

    if args.validate_oir:
        errs = _validate_json(oir, OIR_SCHEMA_PATH)
        if errs:
            print(f"[fail] input O-IR schema validation: {len(errs)} error(s):", file=sys.stderr)
            for i, m in enumerate(errs, 1):
                print(f"  {i:03d}) {m}", file=sys.stderr)
            return 1

    # Apply passes in recommended order: const-fold -> CSE -> DCE
    if args.const_fold:
        try:
            oir = run_const_fold(oir, debug=args.debug)
        except Exception as e:
            print(f"[fail] const-fold error: {e}", file=sys.stderr)
            return 2
    if args.cse:
        try:
            oir = run_cse(oir, debug=args.debug)
        except Exception as e:
            print(f"[fail] CSE error: {e}", file=sys.stderr)
            return 2
    if args.dce:
        try:
            oir = run_dce(oir, debug=args.debug)
        except Exception as e:
            print(f"[fail] DCE error: {e}", file=sys.stderr)
            return 2

    if args.validate_oir:
        errs = _validate_json(oir, OIR_SCHEMA_PATH)
        if errs:
            print(f"[fail] output O-IR schema validation: {len(errs)} error(s):", file=sys.stderr)
            for i, m in enumerate(errs, 1):
                print(f"  {i:03d}) {m}", file=sys.stderr)
            return 1

    try:
        _save_json(oir, out_path)
    except Exception as e:
        print(f"[fail] failed to write O-IR: {e}", file=sys.stderr)
        return 2

    if args.debug:
        sys.stderr.write(f"[ok] wrote optimized O-IR to {out_path}\n")
    else:
        print(f"[ok] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
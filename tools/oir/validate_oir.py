#!/usr/bin/env python3
"""
validate_oir.py

Validate O-IR JSON documents against docs/ir/oir-schema.json using jsonschema.

Usage:
  python tools/oir/validate_oir.py [--schema docs/ir/oir-schema.json] [--examples] [files...]
  python tools/oir/validate_oir.py --stdin

Exit codes:
  0: all documents valid
  1: one or more documents invalid
  2: setup error (schema not found, jsonschema missing, or invalid input)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except Exception:
    jsonschema = None  # type: ignore
    Draft202012Validator = None  # type: ignore


def load_schema(schema_path: Path) -> dict:
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_document(data: object, schema: dict) -> List[str]:
    """Return a list of human-readable error messages; empty if valid."""
    if Draft202012Validator is None:
        raise RuntimeError(
            "python 'jsonschema' package is required.\n"
            "Install with: pip install jsonschema"
        )
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    msgs: List[str] = []
    for err in errors:
        loc = "$"
        if err.path:
            loc = "$." + ".".join(str(p) for p in err.path)
        msgs.append(f"{loc}: {err.message}")
    return msgs


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def discover_example_files() -> List[Path]:
    base = Path("docs/ir/examples/oir")
    if not base.exists():
        return []
    return sorted(p for p in base.glob("*.json") if p.is_file())


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate O-IR JSON files against the O-IR schema")
    ap.add_argument("--schema", default="docs/ir/oir-schema.json", help="Path to oir-schema.json")
    ap.add_argument("--stdin", action="store_true", help="Read a single JSON document from stdin")
    ap.add_argument("--examples", action="store_true", help="Validate all files under docs/ir/examples/oir/")
    ap.add_argument("--verbose", action="store_true", help="Verbose output for valid files")
    ap.add_argument("files", nargs="*", help="Paths to O-IR JSON files")
    args = ap.parse_args(argv)

    if jsonschema is None:
        print("ERROR: python 'jsonschema' package is required.\nInstall with: pip install jsonschema", file=sys.stderr)
        return 2

    schema_path = Path(args.schema)
    try:
        schema = load_schema(schema_path)
    except Exception as e:
        print(f"ERROR: failed to load schema '{schema_path}': {e}", file=sys.stderr)
        return 2

    targets: List[Tuple[str, object]] = []

    if args.stdin:
        try:
            data = json.load(sys.stdin)
        except Exception as e:
            print(f"ERROR: failed to read JSON from stdin: {e}", file=sys.stderr)
            return 2
        targets.append(("stdin", data))

    files: List[Path] = []
    if args.examples:
        files.extend(discover_example_files())
    if args.files:
        files.extend(Path(p) for p in args.files)

    # If no inputs specified, default to examples if present; otherwise print usage hint.
    if not targets and not files:
        ex = discover_example_files()
        if ex:
            files.extend(ex)
        else:
            print("No input specified. Provide files, --examples, or --stdin.", file=sys.stderr)
            return 2

    for p in files:
        try:
            data = load_json(p)
        except Exception as e:
            print(f"[fail] {p}: failed to parse JSON: {e}", file=sys.stderr)
            return 2
        targets.append((str(p), data))

    any_fail = False
    for name, data in targets:
        try:
            errs = validate_document(data, schema)
        except Exception as e:
            print(f"[fail] {name}: validation error: {e}", file=sys.stderr)
            return 2
        if errs:
            any_fail = True
            print(f"[fail] {name}: {len(errs)} error(s):")
            for i, msg in enumerate(errs, 1):
                print(f"  {i:03d}) {msg}")
        else:
            if args.verbose:
                print(f"[ok] {name}")

    if any_fail:
        return 1
    print("[ok] All O-IR documents valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
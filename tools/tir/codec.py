#!/usr/bin/env python3
"""
codec.py

Typed Intermediate Representation (T-IR) codec utilities:
- Load a T-IR JSON document from disk
- Optionally validate it against docs/ir/tir-schema.json using jsonschema
- Dump a T-IR JSON document back to disk with stable formatting

This module is intentionally lightweight and depends only on the Python stdlib
and the optional 'jsonschema' package for validation.

Typical usage:
  from pathlib import Path
  from tools.tir.codec import load_tir, dump_tir, ValidationError

  doc = load_tir(Path("docs/ir/examples/minimal.json"))  # validates by default
  dump_tir(doc, Path("build/tir/minimal.normalized.json"))

CLI helper (pretty print normalized):
  python tools/tir/codec.py docs/ir/examples/minimal.json --stdout
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple

try:
    import jsonschema  # type: ignore
    from jsonschema import Draft202012Validator  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None  # type: ignore
    Draft202012Validator = None  # type: ignore


DEFAULT_SCHEMA_PATH = Path("docs/ir/tir-schema.json")


class ValidationError(Exception):
    """Raised when a T-IR document fails schema validation."""
    def __init__(self, errors: List[str]):
        super().__init__("T-IR validation failed:\n" + "\n".join(errors))
        self.errors = errors


def load_schema(schema_path: Path = DEFAULT_SCHEMA_PATH) -> dict:
    """Load the T-IR JSON Schema."""
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validator(schema: dict):
    if Draft202012Validator is None:
        raise RuntimeError(
            "jsonschema is not installed. Install it with:\n"
            "  pip install jsonschema"
        )
    return Draft202012Validator(schema)


def validate_tir_doc(doc: Any, schema: Optional[dict] = None, schema_path: Path = DEFAULT_SCHEMA_PATH) -> List[str]:
    """
    Validate an in-memory T-IR document. Returns a list of errors; empty if valid.
    If 'schema' is None, loads from 'schema_path'.
    """
    if schema is None:
        schema = load_schema(schema_path)
    validator = _validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
    msgs: List[str] = []
    for err in errors:
        loc = "$"
        if err.path:
            loc = "$." + ".".join(str(p) for p in err.path)
        msgs.append(f"{loc}: {err.message}")
    return msgs


def load_tir(path: Path, *, validate: bool = True, schema_path: Path = DEFAULT_SCHEMA_PATH) -> dict:
    """
    Load a T-IR JSON file from 'path'. If validate=True (default), validates against the schema.
    Raises ValidationError on validation failure.
    """
    if not path.exists():
        raise FileNotFoundError(f"T-IR file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        doc = json.load(f)
    if validate:
        errs = validate_tir_doc(doc, None, schema_path)
        if errs:
            raise ValidationError(errs)
    return doc


def dump_tir(doc: Any, path: Path, *, indent: int = 2, sort_keys: bool = True) -> None:
    """
    Write a T-IR JSON document to 'path' with stable formatting.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(doc, f, indent=indent, ensure_ascii=False, sort_keys=sort_keys)
        f.write("\n")


def _cli(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="T-IR codec: load, optional validate, and pretty-print T-IR JSON")
    ap.add_argument("file", nargs="?", help="Path to T-IR JSON document")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH), help="Path to tir-schema.json")
    ap.add_argument("--no-validate", action="store_true", help="Skip schema validation")
    ap.add_argument("--stdout", action="store_true", help="Write normalized JSON to stdout instead of file")
    ap.add_argument("--out", help="Output path for normalized JSON (implies validation unless --no-validate)")
    ap.add_argument("--pretty", action="store_true", help="Pretty print to stdout (default if --stdout)")
    args = ap.parse_args(argv)

    if args.file is None:
        ap.print_usage(sys.stderr)
        print("error: missing input file", file=sys.stderr)
        return 2

    src = Path(args.file)
    schema_path = Path(args.schema)
    do_validate = not args.no_validate

    try:
        doc = load_tir(src, validate=do_validate, schema_path=schema_path)
    except FileNotFoundError as e:
        print(f"[fail] {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"[fail] {e}", file=sys.stderr)
        return 2
    except ValidationError as ve:
        print(f"[fail] {src}: {len(ve.errors)} error(s):", file=sys.stderr)
        for i, msg in enumerate(ve.errors, 1):
            print(f"  {i:03d}) {msg}", file=sys.stderr)
        return 1

    # Output behavior
    if args.stdout or args.pretty or not args.out:
        # Default to stdout if --stdout or --pretty or no --out specified
        json.dump(doc, sys.stdout, indent=2, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
    if args.out:
        out_path = Path(args.out)
        dump_tir(doc, out_path)
        print(f"[ok] wrote normalized JSON to {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(_cli())
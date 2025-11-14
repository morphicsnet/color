#!/usr/bin/env python3
"""
CGIR Validator CLI

Validates Color Geometry IR (CGIR) JSON files against the JSON Schema and performs
additional semantic checks for determinism-related policies.

Usage examples:
  python tools/cgir/cli_validate.py --in examples/cgir/trace_snn_mix.json
  python tools/cgir/cli_validate.py --in examples/cgir --schema docs/ir/cgir-schema.json
  python tools/cgir/cli_validate.py --in examples/cgir --strict-sum-weights --print-report json

Exit codes:
  0 - all files valid
  1 - one or more files invalid
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Union

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except ImportError as e:
    print("ERROR: jsonschema is required. Install with: pip install jsonschema", file=sys.stderr)
    sys.exit(1)


@dataclass
class FileReport:
    path: Path
    errors: List[str]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_schema(schema_path: Path) -> Dict[str, Any]:
    try:
        schema = _read_json(schema_path)
    except FileNotFoundError:
        print(f"ERROR: Schema file not found: {schema_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse schema JSON at {schema_path}: {e}", file=sys.stderr)
        sys.exit(1)
    return schema


def _iter_json_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        if path.suffix.lower() == ".json":
            yield path
        else:
            # Allow non-.json file if user explicitly passed it; attempt anyway
            yield path
        return
    if path.is_dir():
        for p in sorted(path.rglob("*.json")):
            if p.is_file():
                yield p
        return
    # If not file or dir, still yield to trigger a sensible error downstream
    yield path


def _fmt_json_path(err: jsonschema.exceptions.ValidationError) -> str:
    # Create a dotted path representation to the error location
    if not err.path:
        return "$"
    parts = []
    for seg in err.path:
        if isinstance(seg, int):
            parts.append(f"[{seg}]")
        else:
            # dot for names, bracket for array indices already handled
            if parts:
                parts.append(".")
            parts.append(str(seg))
    return "$" + "".join(parts)


def _approx_equal(x: float, y: float, tol: float = 1e-9) -> bool:
    return abs(x - y) <= tol


def _semantic_checks(instance: Dict[str, Any], strict_sum_weights: bool) -> List[str]:
    errors: List[str] = []

    # Root-level keys checked by schema; here we add semantics
    events = instance.get("events", [])
    if not isinstance(events, list):
        # Schema would already flag this; keep defensive
        errors.append("events: not an array")
        return errors

    for i, evt in enumerate(events):
        prefix = f"events[{i}]"

        # Check mixing weights policy
        mixing = evt.get("mixing", {})
        inputs = mixing.get("inputs", [])
        policy = mixing.get("weights_policy", "normalize")
        if not isinstance(inputs, list) or len(inputs) == 0:
            errors.append(f"{prefix}.mixing.inputs: must be a non-empty array")
        else:
            weights: List[float] = []
            for j, iw in enumerate(inputs):
                try:
                    w = float(iw.get("weight", 0.0))
                except Exception:
                    errors.append(f"{prefix}.mixing.inputs[{j}].weight: not a number")
                    continue
                if w < 0:
                    errors.append(f"{prefix}.mixing.inputs[{j}].weight: negative")
                weights.append(w)

            wsum = sum(weights)
            if policy == "strict_sum_1" or strict_sum_weights:
                if not _approx_equal(wsum, 1.0, 1e-9):
                    errors.append(
                        f"{prefix}.mixing: weights sum {wsum:.12f} != 1 under strict_sum_1"
                    )
            else:
                if wsum <= 0:
                    errors.append(f"{prefix}.mixing: weights sum must be > 0 (got {wsum:.12f})")

        # Check canonical_alpha sums if present
        can = evt.get("canonical_alpha")
        if can is not None:
            alpha_inputs = can.get("inputs", [])
            bias = can.get("bias", 0.0)
            try:
                bias_f = float(bias)
            except Exception:
                errors.append(f"{prefix}.canonical_alpha.bias: not a number")
                bias_f = 0.0

            alphas: List[float] = []
            if isinstance(alpha_inputs, list):
                for j, ent in enumerate(alpha_inputs):
                    try:
                        a = float(ent.get("alpha", 0.0))
                    except Exception:
                        errors.append(f"{prefix}.canonical_alpha.inputs[{j}].alpha: not a number")
                        continue
                    if a < 0:
                        errors.append(f"{prefix}.canonical_alpha.inputs[{j}].alpha: negative")
                    alphas.append(a)
            else:
                errors.append(f"{prefix}.canonical_alpha.inputs: not an array")

            asum = sum(alphas) + bias_f
            if not _approx_equal(asum, 1.0, 1e-9):
                errors.append(
                    f"{prefix}.canonical_alpha: alphas sum {asum:.12f} != 1 (inputs + bias)"
                )

        # Sanity: reachable present and boolean (schema ensures but keep explicit)
        reachable = evt.get("reachable", None)
        if not isinstance(reachable, bool):
            errors.append(f"{prefix}.reachable: must be boolean")

        # Sanity: state objects presence already schema-checked; optionally ensure L in [0,1]
        def _get_ok_state(node_key: str) -> Tuple[bool, float]:
            node = evt.get(node_key)
            if not isinstance(node, dict):
                return (False, 0.0)
            cs = node.get("ok_state") if "ok_state" in node else node.get("state", {}).get("ok_state")
            if not isinstance(cs, dict):
                return (False, 0.0)
            L = cs.get("L")
            return (isinstance(L, (int, float)), float(L) if isinstance(L, (int, float)) else 0.0)

        # Validate that mix_raw_ok and output_state_ok remain within L bounds if present
        for key in ("mix_raw_ok", "after_projection_ok", "output_state_ok"):
            ok, L = _get_ok_state(key)
            if ok and not (0.0 <= L <= 1.0):
                errors.append(f"{prefix}.{key}.ok_state.L: {L} not in [0,1]")

    return errors


def validate_file(file_path: Path, schema: Dict[str, Any], strict_sum_weights: bool) -> FileReport:
    errors: List[str] = []
    try:
        instance = _read_json(file_path)
    except json.JSONDecodeError as e:
        return FileReport(file_path, [f"JSON parse error: {e}"])
    except Exception as e:
        return FileReport(file_path, [f"Read error: {e}"])

    validator = Draft202012Validator(schema)
    schema_errors = list(validator.iter_errors(instance))
    for err in schema_errors:
        jpath = _fmt_json_path(err)
        errors.append(f"SchemaError at {jpath}: {err.message}")

    # Only run semantic checks if schema passed (to reduce noise)
    if not schema_errors:
        errors.extend(_semantic_checks(instance, strict_sum_weights))

    return FileReport(file_path, errors)


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Validate CGIR JSON files")
    ap.add_argument("--in", dest="in_path", required=True, help="Input file or directory")
    ap.add_argument(
        "--schema",
        dest="schema_path",
        default="docs/ir/cgir-schema.json",
        help="Path to CGIR JSON Schema (default: docs/ir/cgir-schema.json)",
    )
    ap.add_argument(
        "--strict-sum-weights",
        action="store_true",
        help="Require mixing weight sums to equal 1.0 even when weights_policy != strict_sum_1",
    )
    ap.add_argument(
        "--print-report",
        choices=["text", "json"],
        default="text",
        help="Output format for report (default: text)",
    )
    args = ap.parse_args(argv)

    in_path = Path(args.in_path)
    schema_path = Path(args.schema_path)
    schema = _load_schema(schema_path)

    any_missing = False
    file_reports: List[FileReport] = []
    for fp in _iter_json_files(in_path):
        if not fp.exists():
            any_missing = True
            file_reports.append(FileReport(fp, [f"Path does not exist: {fp}"]))
            continue
        if fp.is_dir():
            # directories will be expanded by _iter_json_files; still guard
            continue
        rep = validate_file(fp, schema, args.strict_sum_weights)
        file_reports.append(rep)

    failed = [r for r in file_reports if r.errors]
    passed = [r for r in file_reports if not r.errors]

    if args.print_report == "json":
        out = {
            "schema": str(schema_path),
            "input": str(in_path),
            "summary": {"total": len(file_reports), "passed": len(passed), "failed": len(failed)},
            "results": [
                {"path": str(r.path), "status": "ok" if not r.errors else "failed", "errors": r.errors}
                for r in file_reports
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"Schema: {schema_path}")
        print(f"Input:  {in_path}")
        print(f"Total: {len(file_reports)}  Passed: {len(passed)}  Failed: {len(failed)}")
        for r in file_reports:
            status = "OK" if not r.errors else "FAILED"
            print(f"- {r.path}: {status}")
            for e in r.errors:
                print(f"    * {e}")

    return 0 if not failed and not any_missing else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
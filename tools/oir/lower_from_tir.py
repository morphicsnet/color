#!/usr/bin/env python3
"""
lower_from_tir.py

Lower T-IR (typed, proof-aware) to O-IR (optimization-friendly) JSON.

Goals:
- Provide a pass framework scaffold with certificate interfaces.
- Transform basic T-IR modules into valid O-IR modules (placeholder lowering).
- Keep strict JSON Schema compliance for both T-IR and O-IR.

This is an MVP scaffold:
- Validates input against [docs/ir/tir-schema.json](../../docs/ir/tir-schema.json)
- Produces O-IR compliant JSON per [docs/ir/oir-schema.json](../../docs/ir/oir-schema.json)
- Emits empty certificate sets and a minimal, schema-valid function when no lowering rules match.
- Designed to be extended with real passes: proof relevance erasure, DCE, index erasure, closure conversion, etc.

Usage:
  python tools/oir/lower_from_tir.py --in docs/ir/examples/minimal.json --out build/oir/minimal.oir.json
  python tools/oir/lower_from_tir.py --in <TIR.json> --out <OIR.json> --debug --opt 2
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Local helpers
# - T-IR codec (validates by default)
# - O-IR validator (lazy import for post-emit validation)
TIR_SCHEMA_PATH = Path("docs/ir/tir-schema.json")
OIR_SCHEMA_PATH = Path("docs/ir/oir-schema.json")

try:
    from tools.tir.codec import load_tir  # type: ignore
except Exception as e:
    print(
        "ERROR: failed to import tools.tir.codec. Make sure you're running from repo root.\n"
        "Details: {}".format(e),
        file=sys.stderr,
    )
    sys.exit(2)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_oir(doc: Any, schema_path: Path = OIR_SCHEMA_PATH) -> List[str]:
    """Validate O-IR using jsonschema if available; returns list of errors."""
    try:
        import jsonschema  # type: ignore
        from jsonschema import Draft202012Validator  # type: ignore
    except Exception:
        # jsonschema not installed; skip validation but warn.
        return []
    schema = _load_json(schema_path)
    v = Draft202012Validator(schema)
    errs = sorted(v.iter_errors(doc), key=lambda e: e.path)
    msgs: List[str] = []
    for err in errs:
        loc = "$"
        if err.path:
            loc = "$." + ".".join(str(p) for p in err.path)
        msgs.append(f"{loc}: {err.message}")
    return msgs


@dataclass
class PassReport:
    """Collect pass-level certificates and notes."""
    erasure: List[Dict[str, Any]] = field(default_factory=list)
    dce: List[Dict[str, Any]] = field(default_factory=list)
    guards: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_oir_certs(self) -> Dict[str, Any]:
        return {
            "erasure": self.erasure,
            "dce": self.dce,
            "guards": self.guards,
        }


@dataclass
class LowerConfig:
    debug: bool = False
    opt_level: int = 2


class LoweringError(Exception):
    pass


class LowerFromTIR:
    """
    Core lowerer T-IR -> O-IR.

    Extension points:
    - _lower_definition(): term-level lowering
    - _map_type(): type-level lowering
    - _proof_relevance(): classify proof-only items
    - _collect_certificates(): accumulate and export certificates
    """

    def __init__(self, cfg: LowerConfig):
        self.cfg = cfg
        self.report = PassReport()

    # ---- Public API -----------------------------------------------------

    def lower(self, tir: Dict[str, Any]) -> Dict[str, Any]:
        mod = tir.get("module") or {}
        mod_name = mod.get("name") or "Module"

        if self.cfg.debug:
            sys.stderr.write(f"[debug] lowering T-IR module: {mod_name}\n")

        oir_functions: List[Dict[str, Any]] = []
        oir_globals: List[Dict[str, Any]] = []
        oir_tables: List[Dict[str, Any]] = []
        oir_data: List[Dict[str, Any]] = []

        # Lower declarations (very small subset; extend here)
        for decl in mod.get("decls", []):
            # Proof relevance erasure: drop proof-only definitions and record certificate
            if decl.get("kind") == "Definition" and decl.get("proof_relevance") == "proof":
                sym = str(decl.get("name", ""))
                if sym:
                    self.report.erasure.append({"symbol": sym, "reason": "proof-irrelevant"})
                # Do not lower proof-only items into O-IR
                continue

            kind = decl.get("kind")
            if kind == "Definition":
                fn = self._lower_definition(decl)
                if fn is not None:
                    oir_functions.append(fn)
            elif kind == "Inductive":
                # For MVP: record tag spaces and shape metadata elsewhere as needed
                continue

        # Ensure we produce at least one function to satisfy O-IR schema
        if not oir_functions:
            oir_functions.append(self._make_stub_function())

        oir = {
            "version": tir.get("version", "0.1.0"),
            "tool": "coqwasm-oir-lower",
            "module": {
                "name": f"{mod_name}",
                "functions": oir_functions,
                "globals": oir_globals,
                "dataSegments": oir_data,
                "tables": oir_tables,
            },
            "certificates": self.report.to_oir_certs(),
            "metadata": {
                "debug": bool(self.cfg.debug),
                "optLevel": int(self.cfg.opt_level),
            },
        }
        return oir

    # ---- Helpers / Extension points ------------------------------------

    def _lower_definition(self, d: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Lower a DefinitionDecl to an O-IR function if it matches trivial patterns.
        MVP strategy:
        - Detect id-like lambda (fun x => x) and emit a single-block function returning the parameter.
        - Otherwise, skip (future work will perform full lowering).
        """
        name = d.get("name")
        term = d.get("term", {})
        kind = term.get("kind")
        if self.cfg.debug:
            sys.stderr.write(f"[debug] def {name}: term.kind={kind}\n")

        # Heuristic: Lambda x. x  -> id function
        if kind == "Lambda":
            param = term.get("param") or {}
            body = term.get("body") or {}
            if body.get("kind") == "Var" and body.get("name") == param.get("name"):
                # Choose i32 as a placeholder physical type; real lowering will perform repr analysis.
                x_name = str(param.get("name") or "x")
                fn = {
                    "name": str(name),
                    "params": [{"name": x_name, "ty": {"kind": "i32"}}],
                    "results": [{"kind": "i32"}],
                    "blocks": [
                        {
                            "label": "entry",
                            "params": [],
                            "insts": [],
                            "term": {
                                "kind": "Return",
                                "values": [f"%{x_name}"],
                            },
                        }
                    ],
                    "export": True,
                    "attrs": {"pure": True},
                }
                return fn

        # Skip unsupported patterns in MVP
        self.report.notes.append(f"skip definition {name}: unsupported term kind {kind}")
        return None

    def _make_stub_function(self) -> Dict[str, Any]:
        """Produce a schema-valid stub function when nothing lowers."""
        return {
            "name": "stub_entry",
            "params": [],
            "results": [],
            "blocks": [
                {
                    "label": "entry",
                    "params": [],
                    "insts": [],
                    "term": {"kind": "Return", "values": []},
                }
            ],
            "export": False,
            "attrs": {"pure": True},
        }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Lower T-IR JSON to O-IR JSON")
    ap.add_argument("--in", dest="inp", required=True, help="Path to input T-IR JSON")
    ap.add_argument("--out", dest="out", required=True, help="Path to output O-IR JSON")
    ap.add_argument("--opt", type=int, default=2, choices=[0, 1, 2, 3], help="Optimization level (default: 2)")
    ap.add_argument("--debug", action="store_true", help="Enable debug logs")
    ap.add_argument("--validate-oir", action="store_true", help="Validate O-IR output with jsonschema (if available)")
    args = ap.parse_args(argv)

    cfg = LowerConfig(debug=args.debug, opt_level=args.opt)

    # Load and validate T-IR
    tir_path = Path(args.inp)
    try:
        tir = load_tir(tir_path, validate=True, schema_path=TIR_SCHEMA_PATH)
    except Exception as e:
        print(f"[fail] T-IR load/validate error: {e}", file=sys.stderr)
        return 2

    # Lower to O-IR
    lowerer = LowerFromTIR(cfg)
    try:
        oir = lowerer.lower(tir)
    except LoweringError as e:
        print(f"[fail] lowering error: {e}", file=sys.stderr)
        return 2

    # Optional validate O-IR
    if args.validate_oir:
        errs = _validate_oir(oir, OIR_SCHEMA_PATH)
        if errs:
            print(f"[fail] O-IR schema validation: {len(errs)} error(s):", file=sys.stderr)
            for i, m in enumerate(errs, 1):
                print(f"  {i:03d}) {m}", file=sys.stderr)
            return 1

    # Write output
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(oir, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")

    if cfg.debug:
        sys.stderr.write(f"[ok] wrote O-IR to {out_path}\n")
    else:
        print(f"[ok] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
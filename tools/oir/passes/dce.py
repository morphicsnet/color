#!/usr/bin/env python3
"""
dce.py

Dead Code Elimination (DCE) for O-IR JSON modules.

Features:
- Removes unused internal functions (not exported or referenced, including table references) and emits DCE certificates.
- Performs intra-function SSA-style DCE for pure instructions whose results are unused:
  - Pure kinds: Const, Unary, Binary, Select, TagOf, LenOf (no observable side effects assumed).
  - Retains effectful instructions (Load/Store/Call/HeapNew/HeapGet/HeapSet/Guard) even if unused.
- Updates/extends certificates.dce with entries for removed bindings and removed functions.

Schema compliance:
- Input validated optionally against [docs/ir/oir-schema.json](../../../docs/ir/oir-schema.json)
- Output intended to remain valid under the same schema.

Usage:
  python tools/oir/passes/dce.py --in build/oir/minimal.oir.json --out build/oir/minimal.dce.oir.json
  python tools/oir/passes/dce.py --in <in.oir.json> --out <out.oir.json> --validate-oir --debug
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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


def _get_module(doc: Dict[str, Any]) -> Dict[str, Any]:
    mod = doc.get("module")
    if not isinstance(mod, dict):
        raise ValueError("Invalid O-IR: missing 'module' object")
    return mod


def _ensure_certs(doc: Dict[str, Any]) -> Dict[str, Any]:
    certs = doc.get("certificates")
    if certs is None or not isinstance(certs, dict):
        certs = {"erasure": [], "dce": [], "guards": []}
        doc["certificates"] = certs
    certs.setdefault("erasure", [])
    certs.setdefault("dce", [])
    certs.setdefault("guards", [])
    return certs


PURE_INSTRUCTION_KINDS: Set[str] = {
    "Const",
    "Unary",
    "Binary",
    "Select",
    "TagOf",
    "LenOf",
    # Note: We treat Guard as effectful (may trap); do not DCE it.
}


def _value_uses_in_inst(inst: Dict[str, Any]) -> List[str]:
    k = inst.get("kind")
    uses: List[str] = []
    if k == "Const":
        # no args
        pass
    elif k == "Unary":
        uses.append(inst.get("arg", ""))
    elif k == "Binary":
        uses.append(inst.get("lhs", ""))
        uses.append(inst.get("rhs", ""))
    elif k == "Select":
        uses.append(inst.get("cond", ""))
        uses.append(inst.get("ifTrue", ""))
        uses.append(inst.get("ifFalse", ""))
    elif k == "Call":
        for a in inst.get("args", []):
            uses.append(a)
    elif k == "Load":
        addr = inst.get("addr", {})
        if isinstance(addr, dict):
            if "base" in addr:
                uses.append(addr["base"])
    elif k == "Store":
        addr = inst.get("addr", {})
        if isinstance(addr, dict):
            if "base" in addr:
                uses.append(addr["base"])
        if "value" in inst:
            uses.append(inst["value"])
    elif k == "HeapNew":
        for a in inst.get("fields", []):
            uses.append(a)
    elif k == "HeapGet":
        uses.append(inst.get("obj", ""))
    elif k == "HeapSet":
        uses.append(inst.get("obj", ""))
        uses.append(inst.get("value", ""))
    elif k == "TagOf":
        uses.append(inst.get("obj", ""))
    elif k == "LenOf":
        uses.append(inst.get("obj", ""))
    elif k == "Guard":
        uses.append(inst.get("cond", ""))
    # Filter empties and ensure proper formatting
    return [u for u in uses if isinstance(u, str) and u.startswith("%")]


def _result_id(inst: Dict[str, Any]) -> Optional[str]:
    bind = inst.get("bind")
    if isinstance(bind, dict):
        rid = bind.get("result")
        if isinstance(rid, str):
            return rid
    # some instructions allow multiple results via 'binds' array
    # but our current O-IR schema uses single 'bind' except for Call -> 'binds'
    if inst.get("kind") == "Call":
        binds = inst.get("binds", [])
        # we don't DCE multi-result calls (effectful anyway)
        return None
    return None


def _term_uses(term: Dict[str, Any]) -> List[str]:
    k = term.get("kind")
    uses: List[str] = []
    if k == "Return":
        for v in term.get("values", []):
            if isinstance(v, str) and v.startswith("%"):
                uses.append(v)
    elif k == "Br":
        for a in term.get("args", []):
            if isinstance(a, str) and a.startswith("%"):
                uses.append(a)
    elif k == "Switch":
        if isinstance(term.get("on"), str) and term["on"].startswith("%"):
            uses.append(term["on"])
        for c in term.get("cases", []):
            for a in c.get("args", []):
                if isinstance(a, str) and a.startswith("%"):
                    uses.append(a)
    # Trap: no uses
    return uses


def _is_pure(inst: Dict[str, Any]) -> bool:
    return inst.get("kind") in PURE_INSTRUCTION_KINDS


def _function_is_exported(fn: Dict[str, Any]) -> bool:
    return bool(fn.get("export", False))


def _function_linkage(fn: Dict[str, Any]) -> str:
    lk = fn.get("linkage", "internal")
    if lk not in ("internal", "external"):
        return "internal"
    return lk


def _collect_callees(fn: Dict[str, Any]) -> Set[str]:
    callees: Set[str] = set()
    for bb in fn.get("blocks", []):
        for inst in bb.get("insts", []):
            if inst.get("kind") == "Call":
                callee = inst.get("callee")
                if isinstance(callee, str) and callee:
                    callees.add(callee)
    return callees


def _collect_table_refs(mod: Dict[str, Any]) -> Set[str]:
    refs: Set[str] = set()
    for tbl in mod.get("tables", []):
        for sym in tbl.get("elems", []):
            if isinstance(sym, str) and sym:
                refs.add(sym)
    return refs


def dce_functions(mod: Dict[str, Any], certs: Dict[str, Any], debug: bool = False) -> None:
    """Remove unused internal functions and append DCE certificates."""
    fns: List[Dict[str, Any]] = list(mod.get("functions", []))
    name_to_fn: Dict[str, Dict[str, Any]] = {fn.get("name", ""): fn for fn in fns if isinstance(fn.get("name"), str)}
    # Seed used set with exported functions and table refs
    used: Set[str] = set(n for n, fn in name_to_fn.items() if _function_is_exported(fn))
    used |= _collect_table_refs(mod)

    # Fixed-point over call graph
    changed = True
    while changed:
        changed = False
        snapshot = set(used)
        for name in list(snapshot):
            fn = name_to_fn.get(name)
            if fn is None:
                continue
            for callee in _collect_callees(fn):
                if callee not in used and callee in name_to_fn:
                    used.add(callee)
                    changed = True

    # Remove internal functions not used
    kept: List[Dict[str, Any]] = []
    for fn in fns:
        name = fn.get("name", "")
        if name not in used and _function_linkage(fn) == "internal" and not _function_is_exported(fn):
            if debug:
                sys.stderr.write(f"[dce] drop internal unused function {name}\n")
            certs["dce"].append({"symbol": str(name), "kind": "function"})
            continue
        kept.append(fn)

    mod["functions"] = kept


def dce_instructions_in_function(fn: Dict[str, Any], certs: Dict[str, Any], debug: bool = False) -> None:
    """Perform intra-function SSA DCE for pure instructions with unused results."""
    # liveness set of ValueIds
    live: Set[str] = set()

    # 1) From terminators, seed live
    for bb in fn.get("blocks", []):
        term = bb.get("term", {})
        for u in _term_uses(term):
            live.add(u)

    # 2) Reverse-scan each basic block and drop dead pure instructions
    for bb in fn.get("blocks", []):
        insts: List[Dict[str, Any]] = bb.get("insts", [])
        new_insts: List[Dict[str, Any]] = []
        # To maintain order after reverse traversal, push to temp and reverse at end
        temp: List[Dict[str, Any]] = []
        # Build operand use set from all instructions first to handle cross-instruction uses
        for inst in insts:
            for u in _value_uses_in_inst(inst):
                live.add(u)

        for inst in reversed(insts):
            rid = _result_id(inst)
            # If result is used (or instruction has no result), keep it
            if rid is None or rid in live:
                temp.append(inst)
                # Add operands to live (backward dataflow)
                for u in _value_uses_in_inst(inst):
                    live.add(u)
                continue

            # rid defined but not live
            if _is_pure(inst):
                # Drop instruction and record certificate for dead binding
                fn_name = fn.get("name", "")
                sym = f"{fn_name}{rid}"
                if debug:
                    sys.stderr.write(f"[dce] drop dead pure inst result {sym}\n")
                certs["dce"].append({"symbol": sym, "kind": "binding"})
                # Do not add operands to live to allow cascading DCE
                continue
            else:
                # Effectful or unknown kind: must keep; add operands to live
                temp.append(inst)
                for u in _value_uses_in_inst(inst):
                    live.add(u)

        temp.reverse()
        new_insts = temp
        bb["insts"] = new_insts


def dce_instructions(mod: Dict[str, Any], certs: Dict[str, Any], debug: bool = False) -> None:
    for fn in mod.get("functions", []):
        dce_instructions_in_function(fn, certs, debug=debug)


def run_dce(oir: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    certs = _ensure_certs(oir)
    mod = _get_module(oir)
    # Function-level DCE (remove unused internal functions)
    dce_functions(mod, certs, debug=debug)
    # Instruction-level DCE within each function
    dce_instructions(mod, certs, debug=debug)
    return oir


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="O-IR DCE pass (remove dead functions and dead pure bindings)")
    ap.add_argument("--in", dest="inp", required=True, help="Path to input O-IR JSON")
    ap.add_argument("--out", dest="out", required=True, help="Path to output O-IR JSON")
    ap.add_argument("--validate-oir", action="store_true", help="Validate O-IR output with jsonschema (if available)")
    ap.add_argument("--debug", action="store_true", help="Enable debug logs")
    args = ap.parse_args(argv)

    in_path = Path(args.inp)
    out_path = Path(args.out)

    try:
        oir = _load_json(in_path)
    except Exception as e:
        print(f"[fail] failed to read O-IR: {e}", file=sys.stderr)
        return 2

    try:
        oir = run_dce(oir, debug=args.debug)
    except Exception as e:
        print(f"[fail] DCE error: {e}", file=sys.stderr)
        return 2

    if args.validate_oir:
        errs = _validate_json(oir, OIR_SCHEMA_PATH)
        if errs:
            print(f"[fail] O-IR schema validation: {len(errs)} error(s):", file=sys.stderr)
            for i, m in enumerate(errs, 1):
                print(f"  {i:03d}) {m}", file=sys.stderr)
            return 1

    try:
        _save_json(oir, out_path)
    except Exception as e:
        print(f"[fail] failed to write O-IR: {e}", file=sys.stderr)
        return 2

    if args.debug:
        sys.stderr.write(f"[ok] wrote DCE O-IR to {out_path}\n")
    else:
        print(f"[ok] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
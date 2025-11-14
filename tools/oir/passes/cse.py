#!/usr/bin/env python3
"""
cse.py

Common Subexpression Elimination (CSE) for O-IR JSON modules.

MVP features:
- Performs intra-basic-block CSE for Const instructions only.
  - If an identical Const (same type and literal value) appears again in the same block,
    the later binding is replaced with the earlier canonical binding and the duplicate
    Const is removed.
  - Appends DCE-style certificates for removed duplicate Const bindings:
      {"symbol": "<fn_name>%<rid>", "kind": "binding"} to certificates.dce
- Rewrites subsequent instruction operands and the block terminator to reference the
  canonical binding.

Notes:
- This pass is safe and effective when combined with DCE; DCE may remove now-dead bindings.
- Future extensions can include Binary/Unary CSE with algebraic normalization.

Usage (as a library):
    from tools.oir.passes.cse import run_cse
    oir2 = run_cse(oir, debug=True)

CLI integration is provided by higher-level pipelines (e.g., compile_tir_to_oir.py).

Schema:
- Input and output conform to docs/ir/oir-schema.json
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional


def _ensure_certs(doc: Dict[str, Any]) -> Dict[str, Any]:
    certs = doc.get("certificates")
    if certs is None or not isinstance(certs, dict):
        certs = {"erasure": [], "dce": [], "guards": []}
        doc["certificates"] = certs
    certs.setdefault("erasure", [])
    certs.setdefault("dce", [])
    certs.setdefault("guards", [])
    return certs


def _fn_name(fn: Dict[str, Any]) -> str:
    n = fn.get("name")
    return str(n) if isinstance(n, str) else ""


def _value_id(s: Any) -> Optional[str]:
    if isinstance(s, str) and s.startswith("%"):
        return s
    return None


def _rewrite_value(v: Any, repl: Dict[str, str]) -> Any:
    vid = _value_id(v)
    if vid and vid in repl:
        return repl[vid]
    return v


def _rewrite_inst_operands(inst: Dict[str, Any], repl: Dict[str, str]) -> None:
    k = inst.get("kind")
    if k == "Const":
        # no operands to rewrite
        return
    elif k == "Unary":
        inst["arg"] = _rewrite_value(inst.get("arg"), repl)
    elif k == "Binary":
        inst["lhs"] = _rewrite_value(inst.get("lhs"), repl)
        inst["rhs"] = _rewrite_value(inst.get("rhs"), repl)
    elif k == "Select":
        inst["cond"] = _rewrite_value(inst.get("cond"), repl)
        inst["ifTrue"] = _rewrite_value(inst.get("ifTrue"), repl)
        inst["ifFalse"] = _rewrite_value(inst.get("ifFalse"), repl)
    elif k == "Load":
        addr = inst.get("addr") or {}
        if isinstance(addr, dict) and "base" in addr:
            addr["base"] = _rewrite_value(addr.get("base"), repl)
        inst["addr"] = addr
    elif k == "Store":
        addr = inst.get("addr") or {}
        if isinstance(addr, dict) and "base" in addr:
            addr["base"] = _rewrite_value(addr.get("base"), repl)
        inst["addr"] = addr
        inst["value"] = _rewrite_value(inst.get("value"), repl)
    elif k == "HeapNew":
        fields = inst.get("fields") or []
        inst["fields"] = [_rewrite_value(a, repl) for a in fields]
    elif k == "HeapGet":
        inst["obj"] = _rewrite_value(inst.get("obj"), repl)
    elif k == "HeapSet":
        inst["obj"] = _rewrite_value(inst.get("obj"), repl)
        inst["value"] = _rewrite_value(inst.get("value"), repl)
    elif k == "TagOf":
        inst["obj"] = _rewrite_value(inst.get("obj"), repl)
    elif k == "LenOf":
        inst["obj"] = _rewrite_value(inst.get("obj"), repl)
    elif k == "Guard":
        inst["cond"] = _rewrite_value(inst.get("cond"), repl)
    elif k == "Call":
        args = inst.get("args") or []
        inst["args"] = [_rewrite_value(a, repl) for a in args]
    # else: unknown kinds ignored here (schema validator guards evolution)


def _rewrite_term(term: Dict[str, Any], repl: Dict[str, str]) -> None:
    k = term.get("kind")
    if k == "Return":
        vals = term.get("values") or []
        term["values"] = [_rewrite_value(v, repl) for v in vals]
    elif k == "Br":
        args = term.get("args") or []
        term["args"] = [_rewrite_value(a, repl) for a in args]
    elif k == "Switch":
        term["on"] = _rewrite_value(term.get("on"), repl)
        cases = term.get("cases") or []
        for c in cases:
            args = c.get("args") or []
            c["args"] = [_rewrite_value(a, repl) for a in args]
        term["cases"] = cases
    # Trap: no rewrite needed


def _const_key(inst: Dict[str, Any]) -> Optional[Tuple[str, Any]]:
    """
    Returns a key identifying a Const instruction by (type-kind, literal-value).
    Only supports scalar numeric and bool/string payloads carried by 'value'.
    """
    if inst.get("kind") != "Const":
        return None
    val = inst.get("value") or {}
    ty = val.get("ty") or inst.get("bind", {}).get("ty") or {}
    kty = ty.get("kind")
    # Literal value under 'value'
    lit = val.get("value")
    if kty in ("i32", "i64", "f32", "f64", "String", "Bool", "Int", "Int64", "Float"):
        return (str(kty), lit)
    # Default: try to stringify value to be robust
    return (str(kty), lit)


def _result_id(inst: Dict[str, Any]) -> Optional[str]:
    bind = inst.get("bind")
    if isinstance(bind, dict):
        rid = bind.get("result")
        if isinstance(rid, str) and rid.startswith("%"):
            return rid
    return None


def _run_cse_block(fn: Dict[str, Any], bb: Dict[str, Any], certs_dce: List[Dict[str, Any]], debug: bool) -> None:
    """
    Intra-basic-block CSE for Consts:
    - builds canonical map from (type, literal) -> %rid
    - rewrites operands/terminator with replacements
    - drops duplicate Consts and records DCE certificate for removed binding
    """
    const_map: Dict[Tuple[str, Any], str] = {}
    replace_map: Dict[str, str] = {}
    new_insts: List[Dict[str, Any]] = []

    insts = bb.get("insts") or []
    for inst in insts:
        # First, rewrite operands by any known replacements
        _rewrite_inst_operands(inst, replace_map)

        if inst.get("kind") == "Const":
            key = _const_key(inst)
            rid = _result_id(inst)
            if key is not None and rid:
                if key in const_map:
                    # Duplicate constant: redirect its result to canonical rid
                    can = const_map[key]
                    replace_map[rid] = can
                    sym = f"{_fn_name(fn)}{rid}"
                    certs_dce.append({"symbol": sym, "kind": "binding"})
                    if debug:
                        import sys as _sys
                        _sys.stderr.write(f"[cse] drop dup Const {sym} -> {can}\n")
                    # Drop this instruction
                    continue
                else:
                    const_map[key] = rid
        # Keep instruction (rewritten)
        new_insts.append(inst)

    bb["insts"] = new_insts

    # Rewrite terminator
    term = bb.get("term") or {}
    _rewrite_term(term, replace_map)
    bb["term"] = term


def run_cse(oir: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    """
    Run CSE on the provided O-IR document (in-memory). Returns the same dict after mutation.
    """
    certs = _ensure_certs(oir)
    dce_list: List[Dict[str, Any]] = certs.get("dce") or []
    mod = oir.get("module") or {}
    for fn in mod.get("functions") or []:
        for bb in fn.get("blocks") or []:
            _run_cse_block(fn, bb, dce_list, debug=debug)
    certs["dce"] = dce_list
    return oir


__all__ = ["run_cse"]
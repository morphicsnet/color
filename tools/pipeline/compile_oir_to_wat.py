#!/usr/bin/env python3
"""
compile_oir_to_wat.py

Generate a minimal WebAssembly Text (WAT) module from an O-IR JSON module.

Scope (MVP):
- Supports functions with:
  - Params and results of i32/i64/f32/f64 (unit = no result)
  - Single-entry block with either:
    * Return of a single parameter value (e.g., identity function)
    * Return with no values (void/stub)
- Exports functions when export=true
- Ignores instructions for now (expects empty 'insts' arrays), raising on unsupported patterns

This is intended to unblock the "Implement WASM code generator for O-IR" TODO by providing
a minimal, schema-compatible path for the current examples and lowerer output.

Usage:
  python tools/pipeline/compile_oir_to_wat.py --in build/oir/minimal.oir.json --out build/wasm/minimal.wat
  python tools/pipeline/compile_oir_to_wat.py --in <in.oir.json> --out <out.wat> --debug
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_text(txt: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(txt)
        if not txt.endswith("\n"):
            f.write("\n")


def _ty_to_wat(ty: Dict[str, Any]) -> str:
    k = ty.get("kind")
    if k in ("i32", "i64", "f32", "f64"):
        return k
    if k == "unit":
        # represented by no result
        return ""
    raise ValueError(f"unsupported OType in MVP codegen: {k!r}")


def _sanitize_sym(name: str) -> str:
    # WAT symbol-friendly (keep ASCII letters/digits/_/.)
    out = []
    for ch in name:
        if ch.isalnum() or ch in ("_", ".", "/"):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)


def _func_to_wat(fn: Dict[str, Any], debug: bool = False) -> str:
    """
    Convert a minimal O-IR function to WAT.
    Assumptions:
      - zero or one result
      - blocks: one 'entry' block
      - insts: empty (MVP)
      - term: Return with either 0 or 1 value
      - when 1 value: must be a parameter reference (%paramname)
    """
    name = str(fn.get("name", "f"))
    sname = _sanitize_sym(name)
    params = fn.get("params", [])
    results = fn.get("results", [])
    blocks = fn.get("blocks", [])

    # Build parameter map (name -> WAT local symbol)
    # Use declared param names, falling back to p0,p1,...
    param_syms: List[str] = []
    wat_params: List[str] = []
    for i, p in enumerate(params):
        pname = str(p.get("name") or f"p{i}")
        pty = p.get("ty") or {}
        wty = _ty_to_wat(pty)
        psym = _sanitize_sym(pname)
        param_syms.append(psym)
        wat_params.append(f"(param ${psym} {wty})")

    if not isinstance(blocks, list) or len(blocks) == 0:
        raise ValueError(f"function {name}: expected at least one basic block")

    entry = blocks[0]
    insts = entry.get("insts", [])
    term = entry.get("term", {})

    # MVP instruction lowering: support Const/Unary/Binary into locals
    # Collect locals from instruction binds
    locals_map: Dict[str, str] = {}  # local name -> wat type
    inst_lines: List[str] = []

    def _ensure_local(name: str, wty: str) -> None:
        if name not in locals_map:
            locals_map[name] = wty

    def _emit_get(value_id: str) -> str:
        # value_id is like "%x"
        if not isinstance(value_id, str) or not value_id.startswith("%"):
            raise NotImplementedError(f"function {name}: unsupported value ref {value_id!r}")
        sy = value_id[1:]
        if sy in param_syms or sy in locals_map:
            return f"(local.get ${sy})"
        # If the reference matches a param-but-sanitized name (already in param_syms), accept
        raise NotImplementedError(f"function {name}: reference to unknown symbol '{sy}'")

    def _unop_to_wat(op: str) -> Optional[str]:
        mapping = {
            "abs_f32": "f32.abs",
            "abs_f64": "f64.abs",
        }
        return mapping.get(op)

    def _binop_to_wat(op: str) -> Optional[str]:
        mapping = {
            # i32
            "add_i32": "i32.add", "sub_i32": "i32.sub", "mul_i32": "i32.mul",
            "div_s_i32": "i32.div_s", "div_u_i32": "i32.div_u",
            "rem_s_i32": "i32.rem_s", "rem_u_i32": "i32.rem_u",
            "and_i32": "i32.and", "or_i32": "i32.or", "xor_i32": "i32.xor",
            "shl_i32": "i32.shl", "shr_s_i32": "i32.shr_s", "shr_u_i32": "i32.shr_u",
            "eq_i32": "i32.eq", "ne_i32": "i32.ne",
            "lt_s_i32": "i32.lt_s", "lt_u_i32": "i32.lt_u",
            "le_s_i32": "i32.le_s", "le_u_i32": "i32.le_u",
            "gt_s_i32": "i32.gt_s", "gt_u_i32": "i32.gt_u",
            "ge_s_i32": "i32.ge_s", "ge_u_i32": "i32.ge_u",
            # i64
            "add_i64": "i64.add", "sub_i64": "i64.sub", "mul_i64": "i64.mul",
            "div_s_i64": "i64.div_s", "div_u_i64": "i64.div_u",
            "and_i64": "i64.and", "or_i64": "i64.or", "xor_i64": "i64.xor",
            "shl_i64": "i64.shl", "shr_s_i64": "i64.shr_s", "shr_u_i64": "i64.shr_u",
            "eq_i64": "i64.eq", "ne_i64": "i64.ne",
            "lt_s_i64": "i64.lt_s", "le_s_i64": "i64.le_s",
            "gt_s_i64": "i64.gt_s", "ge_s_i64": "i64.ge_s",
            # f32
            "add_f32": "f32.add", "sub_f32": "f32.sub", "mul_f32": "f32.mul", "div_f32": "f32.div",
            "eq_f32": "f32.eq", "ne_f32": "f32.ne", "lt_f32": "f32.lt", "le_f32": "f32.le", "gt_f32": "f32.gt", "ge_f32": "f32.ge",
            # f64
            "add_f64": "f64.add", "sub_f64": "f64.sub", "mul_f64": "f64.mul", "div_f64": "f64.div",
            "eq_f64": "f64.eq", "ne_f64": "f64.ne", "lt_f64": "f64.lt", "le_f64": "f64.le", "gt_f64": "f64.gt", "ge_f64": "f64.ge",
        }
        return mapping.get(op)

    for inst in insts or []:
        k = inst.get("kind")
        if k == "Const":
            bind = inst.get("bind") or {}
            rid = bind.get("result")
            rty = bind.get("ty") or {}
            if not isinstance(rid, str) or not rid.startswith("%"):
                raise NotImplementedError(f"function {name}: Const requires single-result bind with '%'-id")
            lname = rid[1:]
            wty = _ty_to_wat(rty)
            _ensure_local(lname, wty)
            cty = inst.get("value", {}).get("ty") or rty
            wcty = _ty_to_wat(cty)
            if wcty != wty:
                raise NotImplementedError(f"function {name}: Const type mismatch {wcty} vs {wty}")
            cval = inst.get("value", {}).get("value")
            inst_lines.append(f"{wty}.const {cval}")
            inst_lines.append(f"(local.set ${lname})")
        elif k == "Unary":
            op = inst.get("op")
            bind = inst.get("bind") or {}
            rid = bind.get("result")
            rty = bind.get("ty") or {}
            if not isinstance(rid, str) or not rid.startswith("%"):
                raise NotImplementedError(f"function {name}: Unary requires single-result bind with '%'-id")
            lname = rid[1:]
            wty = _ty_to_wat(rty)
            _ensure_local(lname, wty)
            arg = inst.get("arg")
            if op in ("neg_i32", "neg_i64"):
                zty = "i32" if op.endswith("i32") else "i64"
                inst_lines.append(f"{zty}.const 0")
                inst_lines.append(_emit_get(arg))
                inst_lines.append(f"{zty}.sub")
            elif op in ("not_i32", "not_i64"):
                zty = "i32" if op.endswith("i32") else "i64"
                inst_lines.append(f"{zty}.const -1")
                inst_lines.append(_emit_get(arg))
                inst_lines.append(f"{zty}.xor")
            else:
                wop = _unop_to_wat(op or "")
                if not wop:
                    raise NotImplementedError(f"function {name}: unsupported unary op {op!r}")
                inst_lines.append(_emit_get(arg))
                inst_lines.append(wop)
            inst_lines.append(f"(local.set ${lname})")
        elif k == "Binary":
            op = inst.get("op")
            wop = _binop_to_wat(op or "")
            if not wop:
                raise NotImplementedError(f"function {name}: unsupported binary op {op!r}")
            bind = inst.get("bind") or {}
            rid = bind.get("result")
            rty = bind.get("ty") or {}
            if not isinstance(rid, str) or not rid.startswith("%"):
                raise NotImplementedError(f"function {name}: Binary requires single-result bind with '%'-id")
            lname = rid[1:]
            wty = _ty_to_wat(rty)
            _ensure_local(lname, wty)
            lhs = inst.get("lhs")
            rhs = inst.get("rhs")
            inst_lines.append(_emit_get(lhs))
            inst_lines.append(_emit_get(rhs))
            inst_lines.append(wop)
            inst_lines.append(f"(local.set ${lname})")
        elif k == "Select":
            # Lower select: push ifTrue, ifFalse, cond, then 'select', store to local
            bind = inst.get("bind") or {}
            rid = bind.get("result")
            rty = bind.get("ty") or {}
            if not isinstance(rid, str) or not rid.startswith("%"):
                raise NotImplementedError(f"function {name}: Select requires single-result bind with '%'-id")
            lname = rid[1:]
            wty = _ty_to_wat(rty)
            _ensure_local(lname, wty)
            cond = inst.get("cond")
            tval = inst.get("ifTrue")
            fval = inst.get("ifFalse")
            # Stack order: then-value, else-value, cond => select
            inst_lines.append(_emit_get(tval))
            inst_lines.append(_emit_get(fval))
            inst_lines.append(_emit_get(cond))
            inst_lines.append("select")
            inst_lines.append(f"(local.set ${lname})")
        elif k == "Call":
            callee = inst.get("callee")
            if not isinstance(callee, str) or not callee:
                raise NotImplementedError(f"function {name}: Call requires string callee identifier")
            # Push args in order
            for a in inst.get("args", []) or []:
                inst_lines.append(_emit_get(a))
            scallee = _sanitize_sym(callee)
            inst_lines.append(f"(call ${scallee})")
            # Handle zero or one result (MVP: no multi-value)
            binds = inst.get("binds", []) or []
            if len(binds) > 1:
                raise NotImplementedError(f"function {name}: Call with multiple results not supported in MVP")
            if len(binds) == 1:
                b = binds[0] or {}
                rid = b.get("result")
                rty = b.get("ty") or {}
                if not isinstance(rid, str) or not rid.startswith("%"):
                    raise NotImplementedError(f"function {name}: Call requires single-result bind with '%'-id")
                lname = rid[1:]
                wty = _ty_to_wat(rty)
                _ensure_local(lname, wty)
                inst_lines.append(f"(local.set ${lname})")
        elif k in ("Load", "Store", "HeapNew", "HeapGet", "HeapSet", "Guard", "TagOf", "LenOf"):
            raise NotImplementedError(f"function {name}: instruction kind {k!r} not supported in MVP")
        else:
            raise NotImplementedError(f"function {name}: unknown instruction kind {k!r}")

    # param mapping constructed earlier (param_syms, wat_params)

    # Build results
    wat_results: List[str] = []
    if len(results) > 1:
        # MVP: single result only
        raise NotImplementedError(f"function {name}: multiple results not supported in MVP")
    elif len(results) == 1:
        wty = _ty_to_wat(results[0])
        if not wty:
            raise ValueError(f"function {name}: invalid unit type in results")
        wat_results.append(f"(result {wty})")

    # Return lowering (MVP):
    # - Return with 0 values => 'nop'
    # - Return with 1 value referencing param or local
    ret_lines: List[str] = []
    if term.get("kind") != "Return":
        raise NotImplementedError(f"function {name}: only Return terminator supported in MVP")
    ret_vals = term.get("values", [])
    if len(ret_vals) == 0:
        ret_lines.append("nop")
    elif len(ret_vals) == 1:
        v = ret_vals[0]
        if not isinstance(v, str) or not v.startswith("%"):
            raise NotImplementedError(f"function {name}: MVP expects Return of single %symbol value")
        sym = v[1:]
        if sym in param_syms or sym in locals_map:
            ret_lines.append(f"(local.get ${sym})")
        else:
            raise NotImplementedError(f"function {name}: Return references unknown symbol '{sym}'")
    else:
        raise NotImplementedError(f"function {name}: multiple return values not supported in MVP")

    # Function header
    # Attach export if requested
    export_attr = ""
    if bool(fn.get("export", False)):
        export_attr = f'(export "{sname}") '

    header_parts = " ".join(wat_params + wat_results).strip()
    if header_parts:
        header = f"(func ${sname} {header_parts}"
    else:
        header = f"(func ${sname}"

    # Locals declarations (inside func body)
    locals_decls: List[str] = []
    for lname, wty in locals_map.items():
        locals_decls.append(f"(local ${lname} {wty})")

    # Assemble body: locals, lowered instructions, and return lines
    body_lines: List[str] = []
    body_lines.extend(locals_decls)
    body_lines.extend(inst_lines)
    body_lines.extend(ret_lines)
    body = "\n      ".join(body_lines) if body_lines else "nop"
    wat_func = f"  {export_attr}{header}\n      {body}\n  )"
    return wat_func


def oir_to_wat(oir: Dict[str, Any], debug: bool = False) -> str:
    mod = oir.get("module", {})
    if not isinstance(mod, dict):
        raise ValueError("invalid O-IR: missing 'module'")
    fns = mod.get("functions", [])
    if not isinstance(fns, list) or len(fns) == 0:
        # Empty module still valid WAT, but uncommon in our pipeline (lowerer emits stub)
        if debug:
            sys.stderr.write("[warn] O-IR module has no functions; emitting empty module\n")
        return "(module)\n"

    # Emit each function
    fun_txts: List[str] = []
    for fn in fns:
        fun_txts.append(_func_to_wat(fn, debug=debug))

    # Module-level exports are already attached via function export attributes
    # Minimal runtime nucleus: export a single page of linear memory for future heap support
    header = "(module\n  (memory (export \"memory\") 1)\n"
    wat = header + "\n".join(fun_txts) + "\n)\n"
    return wat


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Compile O-IR JSON to WebAssembly Text (WAT)")
    ap.add_argument("--in", dest="inp", required=True, help="Path to O-IR JSON file")
    ap.add_argument("--out", dest="out", required=True, help="Path to WAT output file")
    ap.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = ap.parse_args(argv)

    in_path = Path(args.inp)
    out_path = Path(args.out)

    try:
        oir = _load_json(in_path)
    except Exception as e:
        print(f"[fail] failed to read O-IR: {e}", file=sys.stderr)
        return 2

    try:
        wat = oir_to_wat(oir, debug=args.debug)
    except Exception as e:
        print(f"[fail] codegen error: {e}", file=sys.stderr)
        return 2

    try:
        _save_text(wat, out_path)
    except Exception as e:
        print(f"[fail] failed to write WAT: {e}", file=sys.stderr)
        return 2

    if args.debug:
        sys.stderr.write(f"[ok] wrote WAT to {out_path}\n")
    else:
        print(f"[ok] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
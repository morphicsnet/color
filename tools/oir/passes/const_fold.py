#!/usr/bin/env python3
"""
const_fold.py

Constant folding pass for O-IR JSON modules.

MVP capabilities:
- Intra-basic-block constant folding for:
  - Unary: neg_i32, neg_i64, not_i32, not_i64, abs_f32, abs_f64
  - Binary (integer): add_i32, sub_i32, mul_i32, add_i64, sub_i64, mul_i64
  - Binary (float): add_f32, sub_f32, mul_f32, div_f32, add_f64, sub_f64, mul_f64, div_f64
- When a Unary/Binary has constant operands (produced by prior Consts in the block),
  it is replaced by a Const instruction carrying the folded literal with the same bind.
- The pass updates a local constant environment mapping result ids (e.g., "%r1") to
  (type-kind, literal) pairs to enable cascading folds within the same block.

Non-goals (for now):
- Folding across blocks (no global SSA dataflow)
- Effects, loads/stores, calls, guards, heap ops, tag/len
- Division by zero handling: folding is skipped if encountered

Usage (library):
  from tools.oir.passes.const_fold import run_const_fold
  oir2 = run_const_fold(oir, debug=True)

Schema compliance:
- Input and output adhere to docs/ir/oir-schema.json
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


# ------------- helpers -------------


def _result_id(inst: Dict[str, Any]) -> Optional[str]:
    bind = inst.get("bind")
    if isinstance(bind, dict):
        rid = bind.get("result")
        if isinstance(rid, str) and rid.startswith("%"):
            return rid
    return None


def _bind_type_kind(inst: Dict[str, Any]) -> Optional[str]:
    bind = inst.get("bind")
    if isinstance(bind, dict):
        ty = bind.get("ty")
        if isinstance(ty, dict):
            k = ty.get("kind")
            if isinstance(k, str):
                return k
    return None


def _const_val(inst: Dict[str, Any]) -> Optional[Tuple[str, Any]]:
    """
    If inst is a Const, return (type-kind, literal value) else None.
    """
    if inst.get("kind") != "Const":
        return None
    # Prefer value.ty, else bind.ty
    val = inst.get("value") or {}
    vty = val.get("ty") or {}
    k = vty.get("kind")
    if not isinstance(k, str):
        k = _bind_type_kind(inst)
    lit = val.get("value")
    if isinstance(k, str):
        return (k, lit)
    return None


def _is_value_id(x: Any) -> bool:
    return isinstance(x, str) and x.startswith("%")


# ------------- evaluation core -------------


def _eval_unary(op: str, kty: str, a: Any) -> Optional[Any]:
    try:
        if op == "neg_i32" and kty == "i32":
            return int(-int(a))
        if op == "neg_i64" and kty == "i64":
            return int(-int(a))
        if op == "not_i32" and kty == "i32":
            # bitwise not for 32-bit (two's complement)
            return int(~int(a)) & 0xFFFFFFFF
        if op == "not_i64" and kty == "i64":
            return int(~int(a)) & 0xFFFFFFFFFFFFFFFF
        if op == "abs_f32" and kty == "f32":
            return float(abs(float(a)))
        if op == "abs_f64" and kty == "f64":
            return float(abs(float(a)))
    except Exception:
        return None
    return None


def _eval_binary(op: str, kty: str, a: Any, b: Any) -> Optional[Any]:
    try:
        if kty in ("i32", "i64"):
            ai = int(a)
            bi = int(b)
            if op == "add_i32" and kty == "i32":
                return (ai + bi) & 0xFFFFFFFF
            if op == "sub_i32" and kty == "i32":
                return (ai - bi) & 0xFFFFFFFF
            if op == "mul_i32" and kty == "i32":
                return (ai * bi) & 0xFFFFFFFF
            if op == "add_i64" and kty == "i64":
                return (ai + bi) & 0xFFFFFFFFFFFFFFFF
            if op == "sub_i64" and kty == "i64":
                return (ai - bi) & 0xFFFFFFFFFFFFFFFF
            if op == "mul_i64" and kty == "i64":
                return (ai * bi) & 0xFFFFFFFFFFFFFFFF
        if kty in ("f32", "f64"):
            af = float(a)
            bf = float(b)
            if op == "add_f32" and kty == "f32":
                return af + bf
            if op == "sub_f32" and kty == "f32":
                return af - bf
            if op == "mul_f32" and kty == "f32":
                return af * bf
            if op == "div_f32" and kty == "f32":
                if bf == 0.0:
                    return None
                return af / bf
            if op == "add_f64" and kty == "f64":
                return af + bf
            if op == "sub_f64" and kty == "f64":
                return af - bf
            if op == "mul_f64" and kty == "f64":
                return af * bf
            if op == "div_f64" and kty == "f64":
                if bf == 0.0:
                    return None
                return af / bf
    except Exception:
        return None
    return None


# ------------- pass implementation -------------


def _fold_block(bb: Dict[str, Any], debug: bool = False) -> None:
    """
    Constant fold within a basic block. Mutates the block in place.
    """
    const_env: Dict[str, Tuple[str, Any]] = {}  # %id -> (type-kind, lit)
    new_insts: List[Dict[str, Any]] = []

    for inst in bb.get("insts") or []:
        k = inst.get("kind")

        # Track constants introduced
        if k == "Const":
            rid = _result_id(inst)
            cv = _const_val(inst)
            if rid and cv:
                const_env[rid] = cv
            new_insts.append(inst)
            continue

        if k == "Unary":
            op = inst.get("op")
            rid = _result_id(inst)
            kty = _bind_type_kind(inst)
            arg = inst.get("arg")
            if rid and kty and _is_value_id(arg) and arg in const_env:
                (arg_k, aval) = const_env[arg]
                # bind type determines result kind
                res = _eval_unary(str(op or ""), kty, aval)
                if res is not None:
                    # Replace with Const preserving bind/result type
                    folded = {
                        "kind": "Const",
                        "bind": inst.get("bind"),
                        "value": {
                            "ty": {"kind": kty},
                            "value": res,
                        },
                    }
                    new_insts.append(folded)
                    const_env[rid] = (kty, res)
                    if debug:
                        import sys as _sys
                        _sys.stderr.write(f"[const-fold] Unary {op} -> Const for {rid}\n")
                    continue  # skip original
        elif k == "Binary":
            op = inst.get("op")
            rid = _result_id(inst)
            kty = _bind_type_kind(inst)
            lhs = inst.get("lhs")
            rhs = inst.get("rhs")
            if rid and kty and _is_value_id(lhs) and _is_value_id(rhs) and lhs in const_env and rhs in const_env:
                (_, aval) = const_env[lhs]
                (_, bval) = const_env[rhs]
                res = _eval_binary(str(op or ""), kty, aval, bval)
                if res is not None:
                    folded = {
                        "kind": "Const",
                        "bind": inst.get("bind"),
                        "value": {
                            "ty": {"kind": kty},
                            "value": res,
                        },
                    }
                    new_insts.append(folded)
                    const_env[rid] = (kty, res)
                    if debug:
                        import sys as _sys
                        _sys.stderr.write(f"[const-fold] Binary {op} -> Const for {rid}\n")
                    continue
        # Default: keep instruction unchanged; may use const operands, but not foldable
        new_insts.append(inst)

    bb["insts"] = new_insts
    # Terminator not adjusted for constants (Return of %const will be handled by codegen)


def run_const_fold(oir: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    """
    Run constant folding across all functions/basic-blocks. Returns the mutated O-IR dict.
    """
    mod = oir.get("module") or {}
    for fn in mod.get("functions") or []:
        for bb in fn.get("blocks") or []:
            _fold_block(bb, debug=debug)
    return oir


__all__ = ["run_const_fold"]
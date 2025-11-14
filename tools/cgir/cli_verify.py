#!/usr/bin/env python3
"""
CGIR Cross-Backend Reproducibility Verifier (MVP)

Compares two CGIR artifacts (files or directories) for geometric equivalence:
- Reachability classification for each event (reachable boolean)
- Projected deterministic outputs (output_state_ok.ok_state L,a,b) within tolerance

Usage:
  python tools/cgir/cli_verify.py --a build/cgir/sim --b build/cgir/sim
  python tools/cgir/cli_verify.py --a build/cgir/sim/run1.json --b build/cgir/sim/run2.json --tol 1e-9

Exits 0 when all matched pairs are equivalent under tolerance; nonzero otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

# Ensure 'cgir' package import when running from repo root:
from pathlib import Path as _P
_sys_tools_dir = str(_P(__file__).resolve().parents[1])
if _sys_tools_dir not in sys.path:
    sys.path.insert(0, _sys_tools_dir)

try:
    from cgir.core.numeric import approx_equal, quantize
except Exception as e:
    print("ERROR: Failed to import cgir core modules. Run from repo root or install the package.", file=sys.stderr)
    print(f"Import details: {e}", file=sys.stderr)
    sys.exit(2)


@dataclass
class Diff:
    path_a: Path
    path_b: Path
    issues: List[str]


def _iter_json_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    if path.is_dir():
        for p in sorted(path.rglob("*.json")):
            if p.is_file():
                yield p
        return
    yield path


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _ok_state(node: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Extract an OKLab (L,a,b) triple from a ColorState-like object with ok_state.
    """
    if not isinstance(node, dict):
        raise ValueError("node not a dict")
    s = node.get("ok_state")
    if not isinstance(s, dict):
        raise ValueError("missing ok_state")
    return float(s["L"]), float(s["a"]), float(s["b"])


def _compare_events(ev_a: Dict[str, Any], ev_b: Dict[str, Any], tol: float) -> List[str]:
    issues: List[str] = []

    # reachable boolean
    ra = bool(ev_a.get("reachable", False))
    rb = bool(ev_b.get("reachable", False))
    if ra != rb:
        issues.append(f"reachable mismatch: {ra} vs {rb}")

    # output_state_ok
    try:
        La, aa, ba = _ok_state(ev_a.get("output_state_ok", {}))
        Lb, ab, bb = _ok_state(ev_b.get("output_state_ok", {}))
        if not (approx_equal(La, Lb, tol) and approx_equal(aa, ab, tol) and approx_equal(ba, bb, tol)):
            issues.append(f"output_state_ok mismatch: A=({La:.12f},{aa:.12f},{ba:.12f}) vs B=({Lb:.12f},{ab:.12f},{bb:.12f}) tol={tol}")
    except Exception as e:
        issues.append(f"output_state_ok missing or invalid: {e}")

    return issues


def _rel_key(base: Path, p: Path) -> str:
    return p.name if base.is_file() else p.relative_to(base).as_posix()


def verify_pair(pa: Path, pb: Path, tol: float) -> Diff:
    issues: List[str] = []
    try:
        a = _read_json(pa)
        b = _read_json(pb)
    except Exception as e:
        return Diff(pa, pb, [f"read error: {e}"])

    ev_a = a.get("events", [])
    ev_b = b.get("events", [])
    if not isinstance(ev_a, list) or not isinstance(ev_b, list):
        return Diff(pa, pb, ["events must be lists"])

    if len(ev_a) != len(ev_b):
        issues.append(f"number of events mismatch: {len(ev_a)} vs {len(ev_b)}")

    # Compare up to min length to report event-wise issues
    for i in range(min(len(ev_a), len(ev_b))):
        sub = _compare_events(ev_a[i], ev_b[i], tol)
        issues.extend([f"event[{i}]: {m}" for m in sub])

    return Diff(pa, pb, issues)


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="CGIR verifier: compare reachability and outputs across two artifacts")
    ap.add_argument("--a", dest="path_a", required=True, help="First file or directory")
    ap.add_argument("--b", dest="path_b", required=True, help="Second file or directory")
    ap.add_argument("--tol", dest="tol", type=float, default=1e-12, help="Tolerance for OKLab component comparison")
    args = ap.parse_args(argv)

    a = Path(args.path_a).resolve()
    b = Path(args.path_b).resolve()

    files_a = list(_iter_json_files(a))
    files_b = list(_iter_json_files(b))

    # Build keyed maps by relative key
    map_a = { _rel_key(a, p): p for p in files_a if p.exists() }
    map_b = { _rel_key(b, p): p for p in files_b if p.exists() }

    # Pair by intersection of keys
    common = sorted(set(map_a.keys()) & set(map_b.keys()))
    missing_a = sorted(set(map_b.keys()) - set(map_a.keys()))
    missing_b = sorted(set(map_a.keys()) - set(map_b.keys()))

    diffs: List[Diff] = []
    for k in common:
        diffs.append(verify_pair(map_a[k], map_b[k], args.tol))

    had_missing = False
    if missing_a:
        print(f"WARNING: {len(missing_a)} files present in B but missing in A (skipping):")
        for k in missing_a[:10]:
            print(f"  - {k}")
        had_missing = True
    if missing_b:
        print(f"WARNING: {len(missing_b)} files present in A but missing in B (skipping):")
        for k in missing_b[:10]:
            print(f"  - {k}")
        had_missing = True

    failures = [d for d in diffs if d.issues]
    for d in diffs:
        status = "OK" if not d.issues else "FAILED"
        print(f"- {d.path_a} ↔ {d.path_b}: {status}")
        for iss in d.issues:
            print(f"    * {iss}")

    # Exit code policy: nonzero if any diffs failed or missing files existed
    return 0 if (not failures and not had_missing) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
#!/usr/bin/env python3
"""
smoke_test.py

End-to-end smoke tests for the current Coq→WASM pipeline.

Covers:
1) T-IR minimal example → O-IR → WAT, assert identity function export and body
2) O-IR arithmetic example (add_i32) → WAT, assert export and i32.add present
3) T-IR proof-only example → O-IR erasure → WAT, assert empty module (no funcs)

Usage:
  PYTHONPATH=. python tools/pipeline/smoke_test.py --verbose
  PYTHONPATH=. python tools/pipeline/smoke_test.py

Requirements:
- jsonschema (optional) for validation flags already handled by the subcommands.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def run(cmd: list[str], verbose: bool = False) -> tuple[int, str, str]:
    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**dict(**{**dict()}, **dict(**{**{}})), "PYTHONPATH": str(REPO_ROOT)},
    )
    out, err = proc.communicate()
    if verbose:
        sys.stdout.write(f"$ {' '.join(cmd)}\n")
        if out:
            sys.stdout.write(out)
        if err:
            sys.stderr.write(err)
    return proc.returncode, out, err


def expect_file_contains(path: Path, needle: str, desc: str) -> None:
    if not path.exists():
        raise AssertionError(f"expected file does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        raise AssertionError(f"expected '{needle}' in {path} ({desc})")


def expect_no_func_in_wat(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"WAT not found: {path}")
    text = path.read_text(encoding="utf-8")
    if "(func " in text:
        raise AssertionError(f"expected empty module without functions in {path}")


def test_tir_minimal(verbose: bool) -> None:
    # Validate T-IR examples (sanity)
    code, _, _ = run(["python3", "tools/tir/validate_tir.py", "--examples", "--verbose"], verbose)
    if code != 0:
        raise AssertionError("T-IR validation failed")

    # T-IR → O-IR → WAT
    wat = REPO_ROOT / "build/wasm/minimal_from_tir.wat"
    oir = REPO_ROOT / "build/oir/minimal_from_tir.oir.json"
    code, _, _ = run([
        "python3", "tools/pipeline/compile_tir_to_wat.py",
        "--in", "docs/ir/examples/minimal.json",
        "--out-wat", str(wat.relative_to(REPO_ROOT)),
        "--oir-out", str(oir.relative_to(REPO_ROOT)),
        "--validate-oir",
        "--dce",
    ], verbose)
    if code != 0:
        raise AssertionError("compile_tir_to_wat.py failed for minimal.json")

    # Assert the id function export and body exist
    expect_file_contains(wat, '(export "id")', "id export")
    expect_file_contains(wat, "(local.get $x)", "id body local.get")


def test_oir_add_i32(verbose: bool) -> None:
    # Validate O-IR example
    code, _, _ = run(["python3", "tools/oir/validate_oir.py", "docs/ir/examples/oir/add_i32.json", "--verbose"], verbose)
    if code != 0:
        raise AssertionError("O-IR validation failed for add_i32.json")

    wat = REPO_ROOT / "build/wasm/add_i32.wat"
    code, _, _ = run([
        "python3", "tools/pipeline/compile_oir_to_wat.py",
        "--in", "docs/ir/examples/oir/add_i32.json",
        "--out", str(wat.relative_to(REPO_ROOT)),
    ], verbose)
    if code != 0:
        raise AssertionError("compile_oir_to_wat.py failed for add_i32.json")

    # Assert export and instruction presence
    expect_file_contains(wat, '(export "add_i32")', "add_i32 export")
    expect_file_contains(wat, "i32.add", "add_i32 body has i32.add")


def test_tir_proof_only(verbose: bool) -> None:
    # T-IR → O-IR → WAT for proof-only example (erasure leads to empty module)
    wat = REPO_ROOT / "build/wasm/proof_only_from_tir.wat"
    code, _, _ = run([
        "python3", "tools/pipeline/compile_tir_to_wat.py",
        "--in", "docs/ir/examples/proof_only.json",
        "--out-wat", str(wat.relative_to(REPO_ROOT)),
        "--validate-oir",
        "--dce",
    ], verbose)
    if code != 0:
        raise AssertionError("compile_tir_to_wat.py failed for proof_only.json")

    expect_file_contains(wat, "(module", "WAT module")
    expect_no_func_in_wat(wat)


def main() -> int:
    ap = argparse.ArgumentParser(description="Pipeline smoke tests (T-IR/O-IR → WAT)")
    ap.add_argument("--verbose", action="store_true", help="Verbose subcommand output")
    args = ap.parse_args()

    try:
        test_tir_minimal(args.verbose)
        test_oir_add_i32(args.verbose)
        test_tir_proof_only(args.verbose)
    except AssertionError as e:
        sys.stderr.write(f"[fail] {e}\n")
        return 1
    except Exception as e:
        sys.stderr.write(f"[error] unexpected: {e}\n")
        return 2

    print("[ok] Smoke tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
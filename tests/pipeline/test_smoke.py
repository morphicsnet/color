#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path


def _run(cmd, cwd: Path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(cwd)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # Echo output to aid debugging on CI failures
    print("CMD:", " ".join(cmd))
    print("STDOUT:\n", proc.stdout)
    print("STDERR:\n", proc.stderr, file=sys.stderr)
    return proc.returncode


def test_pipeline_smoke():
    """
    End-to-end smoke: T-IR -> O-IR -> WAT.
    Delegates to tools/pipeline/smoke_test.py which performs:
      - T-IR validation
      - T-IR minimal -> O-IR -> WAT (id function)
      - O-IR add_i32 -> WAT (i32.add)
      - T-IR proof-only -> WAT (empty module)
    """
    repo_root = Path(__file__).resolve().parents[2]
    code = _run([sys.executable, "tools/pipeline/smoke_test.py"], repo_root)
    assert code == 0, "pipeline smoke test failed"
import json
from pathlib import Path

import pytest

try:
    from jsonschema import Draft202012Validator
except Exception as e:
    pytest.skip(f"jsonschema not available: {e}", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs" / "ir" / "cgir-schema.json"
EXAMPLES_DIR = REPO_ROOT / "examples" / "cgir"
EXAMPLE_POSITIVE = EXAMPLES_DIR / "trace_snn_mix.json"
EXAMPLE_NEGATIVE = EXAMPLES_DIR / "trace_unreachable_projection.json"


def _read_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_examples_validate_against_schema():
    schema = _read_json(SCHEMA_PATH)
    v = Draft202012Validator(schema)

    for p in [EXAMPLE_POSITIVE, EXAMPLE_NEGATIVE]:
        inst = _read_json(p)
        errs = list(v.iter_errors(inst))
        msgs = [f"{list(e.path)}: {e.message}" for e in errs]
        assert not errs, f"{p.name} failed schema validation:\n" + "\n".join(msgs)


def test_positive_example_reachable_true_and_projection_identity():
    inst = _read_json(EXAMPLE_POSITIVE)
    assert "events" in inst and isinstance(inst["events"], list) and inst["events"], "events missing"
    ev = inst["events"][0]

    assert ev["reachable"] is True

    raw = ev["mix_raw_ok"]["ok_state"]
    proj = ev["after_projection_ok"]["ok_state"]
    # Projection was identity in the positive example
    assert (raw["L"], raw["a"], raw["b"]) == (proj["L"], proj["a"], proj["b"])


def test_negative_example_unreachable_and_projection_changes_point():
    inst = _read_json(EXAMPLE_NEGATIVE)
    assert "events" in inst and isinstance(inst["events"], list) and inst["events"], "events missing"
    ev = inst["events"][0]

    assert ev["reachable"] is False

    raw = ev["mix_raw_ok"]["ok_state"]
    proj = ev["after_projection_ok"]["ok_state"]

    # Projection should move the point (outside droplet to boundary)
    assert (raw["L"], raw["a"], raw["b"]) != (proj["L"], proj["a"], proj["b"])
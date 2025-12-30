"""
Tests for CGIR builder and geometric IR functionality.
"""

import pytest
from oklab_grounding.cgir import CGIRBuilder, SpaceDefinition, StateVariable, Interaction, Operator, GeometricIntent


class TestCGIRBuilder:
    def test_create_empty_cgir(self):
        builder = CGIRBuilder()
        cgir = builder.to_dict()

        assert cgir["cgir_version"] == "0.1.0"
        assert "spaces" not in cgir
        assert "state" not in cgir
        assert "interactions" not in cgir

    def test_add_space(self):
        builder = CGIRBuilder()
        space = SpaceDefinition(
            id="test_space",
            kind="riemannian",
            dim=3,
            coords="test_coords"
        )
        builder.add_space(space)

        cgir = builder.to_dict()
        assert len(cgir["spaces"]) == 1
        assert cgir["spaces"][0]["id"] == "test_space"

    def test_add_state_variable(self):
        builder = CGIRBuilder()
        var = StateVariable(
            id="test_var",
            space="test_space",
            kind="point",
            value={"x": 1.0, "y": 2.0}
        )
        builder.add_state_variable(var)

        cgir = builder.to_dict()
        assert len(cgir["state"]) == 1
        assert cgir["state"][0]["id"] == "test_var"

    def test_add_interaction(self):
        builder = CGIRBuilder()
        interaction = Interaction(
            id="test_interaction",
            space="test_space",
            kind="convex_mix",
            inputs=["var1", "var2"]
        )
        builder.add_interaction(interaction)

        cgir = builder.to_dict()
        assert len(cgir["interactions"]) == 1
        assert cgir["interactions"][0]["kind"] == "convex_mix"

    def test_add_intent(self):
        builder = CGIRBuilder()
        intent = GeometricIntent(
            time=0.0,
            kind="state_injection",
            target="test_var",
            params={"value": {"x": 5.0}}
        )
        builder.add_intent(intent)

        cgir = builder.to_dict()
        assert len(cgir["events"]) == 1
        assert cgir["events"][0]["kind"] == "state_injection"

    def test_simulation_basic(self):
        builder = CGIRBuilder()

        # Add a simple state variable
        var = StateVariable(
            id="test_var",
            space="test_space",
            kind="point",
            value={"x": 1.0}
        )
        builder.add_state_variable(var)

        # Simulate for a few steps
        trajectory = builder.simulate(steps=3)

        assert len(trajectory) == 3
        assert trajectory[0]["step"] == 0
        assert trajectory[1]["step"] == 1
        assert trajectory[2]["step"] == 2

        # State should be preserved
        assert trajectory[0]["state"]["test_var"]["x"] == 1.0

    def test_simulation_with_intent(self):
        builder = CGIRBuilder()

        # Add state variable
        var = StateVariable(
            id="test_var",
            space="test_space",
            kind="point",
            value={"x": 1.0}
        )
        builder.add_state_variable(var)

        # Add intent to modify state
        intent = GeometricIntent(
            time=0.0,
            kind="state_injection",
            target="test_var",
            params={"value": {"x": 5.0}}
        )
        builder.add_intent(intent)

        trajectory = builder.simulate(steps=2)

        # First step should have modified value
        assert trajectory[0]["state"]["test_var"]["x"] == 5.0
        # Second step should maintain the value
        assert trajectory[1]["state"]["test_var"]["x"] == 5.0

    def test_json_roundtrip(self):
        builder = CGIRBuilder()
        space = SpaceDefinition(id="test", kind="riemannian", dim=3, coords="test")
        builder.add_space(space)

        # Convert to JSON and back
        json_str = builder.to_json()
        loaded_builder = CGIRBuilder.from_json(json_str)

        loaded_cgir = loaded_builder.to_dict()
        assert loaded_cgir["spaces"][0]["id"] == "test"


class TestGeometricIR:
    def test_backward_compatibility(self):
        """Test that CGIR can still represent legacy neuron-based simulations."""
        builder = CGIRBuilder()

        # Add legacy-style neuron
        builder.add_neuron({
            "id": "n1",
            "state": {"ok_state": {"L": 0.5, "a": 0.1, "b": 0.2}},
            "role": "presynaptic"
        })

        # Add legacy event
        builder.add_event({
            "t_ms": 0,
            "target": {"id": "n1"},
            "mixing": {
                "inputs": [{"source": {"id": "n1"}, "weight": 1.0}]
            },
            "mix_raw_ok": {"ok_state": {"L": 0.5, "a": 0.1, "b": 0.2}},
            "after_projection_ok": {"ok_state": {"L": 0.5, "a": 0.1, "b": 0.2}},
            "reachable": True,
            "output_state_ok": {"ok_state": {"L": 0.5, "a": 0.1, "b": 0.2}}
        })

        cgir = builder.to_dict()
        assert "neurons" in cgir
        assert "events" in cgir
        assert len(cgir["neurons"]) == 1
        assert len(cgir["events"]) == 1
"""
CGIR (Color Geometry Intermediate Representation) builder and utilities.

Supports both legacy CGIR format and generalized geometric IR format.
"""

from typing import Dict, List, Any, Optional, Union
import json
from dataclasses import dataclass, asdict
from .space import OKLabSpace
from .oklab import OKLab

@dataclass
class SpaceDefinition:
    """Geometric manifold definition."""
    id: str
    kind: str  # "riemannian", "discrete", "statistical"
    dim: int
    coords: str
    metric: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None

@dataclass
class StateVariable:
    """State variable living on a manifold."""
    id: str
    space: str
    kind: str  # "point", "vector", "field", "neuron"
    value: Any
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class Interaction:
    """Energy term or coupling between state variables."""
    id: str
    space: str
    kind: str  # "convex_mix", "quadratic_potential", "constraint", "coupling"
    inputs: Optional[List[str]] = None
    params: Optional[Dict[str, Any]] = None
    energy: Optional[str] = None

@dataclass
class Operator:
    """Canonical geometric operator."""
    id: str
    space: str
    kind: str  # "distance", "flow", "metric_evolution", "time_step", "optimization"
    backend: str
    params: Optional[Dict[str, Any]] = None

@dataclass
class GeometricIntent:
    """Typed intent for geometric operations."""
    time: float
    kind: str  # "state_injection", "boundary_update", "topology_intent", "operator_step", "metric_update"
    space: Optional[str] = None
    target: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    justification: Optional[str] = None

class CGIRBuilder:
    """
    Builder for CGIR (Color Geometry Intermediate Representation).

    Supports both legacy format and generalized geometric IR format.
    """

    def __init__(self, version: str = "0.1.0"):
        self.version = version
        self.spaces: List[SpaceDefinition] = []
        self.state: List[StateVariable] = []
        self.interactions: List[Interaction] = []
        self.operators: List[Operator] = []
        self.intents: List[GeometricIntent] = []

        # Legacy CGIR fields for backward compatibility
        self.droplet: Optional[Dict[str, Any]] = None
        self.neurons: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []

    def add_space(self, space: SpaceDefinition) -> None:
        """Add a geometric manifold definition."""
        self.spaces.append(space)

    def add_state_variable(self, var: StateVariable) -> None:
        """Add a state variable living on a manifold."""
        self.state.append(var)

    def add_interaction(self, interaction: Interaction) -> None:
        """Add an energy term or coupling."""
        self.interactions.append(interaction)

    def add_operator(self, operator: Operator) -> None:
        """Add a canonical geometric operator."""
        self.operators.append(operator)

    def add_intent(self, intent: GeometricIntent) -> None:
        """Add a geometric intent."""
        self.intents.append(intent)

    # Legacy methods for backward compatibility
    def set_droplet(self, droplet: Dict[str, Any]) -> None:
        """Set legacy droplet configuration."""
        self.droplet = droplet

    def add_neuron(self, neuron: Dict[str, Any]) -> None:
        """Add legacy neuron."""
        self.neurons.append(neuron)

    def add_event(self, event: Dict[str, Any]) -> None:
        """Add legacy event."""
        self.events.append(event)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "cgir_version": self.version
        }

        # Add generalized geometric IR fields if present
        if self.spaces:
            result["spaces"] = [asdict(space) for space in self.spaces]
        if self.state:
            result["state"] = [asdict(var) for var in self.state]
        if self.interactions:
            result["interactions"] = [asdict(interaction) for interaction in self.interactions]
        if self.operators:
            result["operators"] = [asdict(op) for op in self.operators]
        if self.intents:
            result["events"] = [asdict(intent) for intent in self.intents]

        # Add legacy fields if present
        if self.droplet:
            result["droplet"] = self.droplet
        if self.neurons:
            result["neurons"] = self.neurons
        if self.events and not self.intents:  # Don't overwrite if we have intents
            result["events"] = self.events

        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: str) -> None:
        """Save CGIR to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CGIRBuilder':
        """Create CGIRBuilder from dictionary."""
        builder = cls(data.get("cgir_version", "0.1.0"))

        # Load generalized fields
        if "spaces" in data:
            builder.spaces = [SpaceDefinition(**space) for space in data["spaces"]]
        if "state" in data:
            builder.state = [StateVariable(**var) for var in data["state"]]
        if "interactions" in data:
            builder.interactions = [Interaction(**interaction) for interaction in data["interactions"]]
        if "operators" in data:
            builder.operators = [Operator(**op) for op in data["operators"]]

        # Load intents vs legacy events
        if "events" in data:
            events = data["events"]
            if events and "kind" in events[0]:  # Check if these are geometric intents
                builder.intents = [GeometricIntent(**intent) for intent in events]
            else:  # Legacy events
                builder.events = events

        # Load legacy fields
        if "droplet" in data:
            builder.droplet = data["droplet"]
        if "neurons" in data:
            builder.neurons = data["neurons"]

        return builder

    @classmethod
    def from_json(cls, json_str: str) -> 'CGIRBuilder':
        """Create CGIRBuilder from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def load(cls, path: str) -> 'CGIRBuilder':
        """Load CGIR from JSON file."""
        with open(path, 'r') as f:
            return cls.from_dict(json.load(f))

    def simulate(self, steps: int = 100, dt: float = 0.01) -> List[Dict[str, Any]]:
        """
        Run geometric simulation over time steps.

        Processes interactions and intents to evolve state variables on manifolds.
        """
        # Initialize state from CGIR state variables
        current_state = {var.id: var.value for var in self.state}

        trajectory = []
        current_time = 0.0

        for step in range(steps):
            # Record current state
            state_snapshot = {
                "step": step,
                "time": current_time,
                "state": current_state.copy()
            }
            trajectory.append(state_snapshot)

            # Process interactions (energy minimization, couplings)
            for interaction in self.interactions:
                self._process_interaction(interaction, current_state)

            # Process intents (geometric operations)
            for intent in self.intents:
                if intent.time <= current_time:
                    self._process_intent(intent, current_state)

            current_time += dt

        return trajectory

    def _process_interaction(self, interaction: Interaction, state: Dict[str, Any]) -> None:
        """
        Process a single interaction (energy term or coupling).
        """
        kind = interaction.kind
        space_id = interaction.space

        if kind == "convex_mix" and space_id == "oklab":
            # OKLab convex mixing
            self._process_convex_mix(interaction, state)
        # Add more interaction types as needed...

    def _process_convex_mix(self, interaction: Interaction, state: Dict[str, Any]) -> None:
        """
        Process convex mixing interaction in OKLab space.
        """
        inputs = interaction.inputs or []
        if len(inputs) < 2:
            return

        # Get input values from state
        input_values = []
        weights = []

        for input_id in inputs:
            if input_id in state:
                input_values.append(state[input_id])
                # Use equal weights if not specified
                weights.append(1.0 / len(inputs))

        if len(input_values) >= 2:
            # Perform mixing using OKLab space
            from .oklab import OKLabSpace
            space = OKLabSpace()

            # Convert dict values to OKLab objects if needed
            oklab_values = []
            for val in input_values:
                if isinstance(val, dict) and 'L' in val:
                    oklab_values.append(OKLab(val['L'], val['a'], val['b']))
                else:
                    oklab_values.append(val)

            result = space.mix(oklab_values, weights)

            # Update target state (assume first input is target for simplicity)
            target_id = inputs[0]
            state[target_id] = {'L': result.L, 'a': result.a, 'b': result.b}

    def _process_intent(self, intent: GeometricIntent, state: Dict[str, Any]) -> None:
        """
        Process a geometric intent.
        """
        kind = intent.kind

        if kind == "state_injection":
            # Inject value into state variable
            target = intent.target
            value = intent.params.get('value') if intent.params else None
            if target and value is not None:
                state[target] = value
        # Add more intent types as needed...
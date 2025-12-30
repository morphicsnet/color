/**
 * Geometric IR (GroundIR) interfaces and CGIR builder.
 *
 * Supports generalized geometric computing with manifolds, state, interactions, and intents.
 */

import type { OKLab } from '@oklab/core';

export type ID = string; // Stable identifier

// Geometric manifold definition
export interface Space {
  id: ID;
  kind: 'riemannian' | 'discrete' | 'statistical';
  dim: number;
  coords: string; // Coordinate system name
  metric?: string; // Metric identifier
  constraints?: {
    regions?: Array<{
      id: ID;
      type: string;
      params?: Record<string, any>;
    }>;
  };
}

// State variable living on a manifold
export interface StateVariable {
  id: ID;
  space: ID; // Reference to space this variable lives on
  kind: 'point' | 'vector' | 'field' | 'neuron';
  value: any; // Current value in coordinate system
  metadata?: Record<string, any>;
}

// Energy term or coupling between state variables (PhysIR Φ)
export interface Interaction {
  id: ID;
  space: ID;
  kind: 'convex_mix' | 'quadratic_potential' | 'constraint' | 'coupling';
  inputs?: ID[];
  params?: Record<string, any>;
  energy?: string; // Energy functional expression
}

// Canonical geometric operator
export interface Operator {
  id: ID;
  space: ID;
  kind: 'distance' | 'flow' | 'metric_evolution' | 'time_step' | 'optimization';
  backend: string; // Implementation backend identifier
  params?: Record<string, any>;
}

// Typed intent for geometric operations
export interface GeometricIntent {
  time: number;
  kind: 'state_injection' | 'boundary_update' | 'topology_intent' | 'operator_step' | 'metric_update';
  space?: ID;
  target?: ID;
  params?: Record<string, any>;
  justification?: string;
}

// Legacy CGIR types for backward compatibility
export interface ColorState {
  ok_state?: { L: number; a: number; b: number };
  lch_state?: { L: number; C: number; h: number };
}

export interface Neuron {
  id: ID;
  role?: 'presynaptic' | 'postsynaptic' | 'interneuron' | 'bias';
  state: ColorState;
  notes?: string;
}

export interface EventEntry {
  t_ms: number;
  target: { id: ID };
  mixing: {
    inputs: Array<{ source: { id: ID }; weight: number }>;
    weights_policy?: 'normalize' | 'strict_sum_1';
    sum_assertion?: number;
  };
  mix_raw_ok: ColorState;
  after_projection_ok: ColorState;
  reachable: boolean;
  canonical_alpha: {
    inputs: Array<{ source: { id: ID }; alpha: number }>;
    bias?: number;
  };
  output_state_ok: ColorState;
  provenance?: any;
}

export interface SimulationStep {
  step: number;
  time: number;
  state: Record<string, any>;
}

export interface Droplet {
  projection: {
    cmax_ref: string;
    rule: 'radial_clamp';
    tol?: number;
  };
  canonicalization: {
    rule: 'gray_axis_bias';
    tol?: number;
  };
}

// Generalized CGIR that supports both legacy and geometric IR
export interface CGIR {
  cgir_version: string;

  // Generalized geometric IR fields
  spaces?: Space[];
  state?: StateVariable[];
  interactions?: Interaction[];
  operators?: Operator[];

  // Events can be legacy EventEntry or new GeometricIntent
  events?: (EventEntry | GeometricIntent)[];

  // Legacy CGIR fields
  droplet?: Droplet;
  neurons?: Neuron[];
}

export class CGIRBuilder {
  private cgir: Partial<CGIR> = { cgir_version: '0.1.0' };

  constructor(version?: string) {
    if (version) this.cgir.cgir_version = version;
  }

  addSpace(space: Space): CGIRBuilder {
    if (!this.cgir.spaces) this.cgir.spaces = [];
    this.cgir.spaces.push(space);
    return this;
  }

  addStateVariable(variable: StateVariable): CGIRBuilder {
    if (!this.cgir.state) this.cgir.state = [];
    this.cgir.state.push(variable);
    return this;
  }

  addInteraction(interaction: Interaction): CGIRBuilder {
    if (!this.cgir.interactions) this.cgir.interactions = [];
    this.cgir.interactions.push(interaction);
    return this;
  }

  addOperator(operator: Operator): CGIRBuilder {
    if (!this.cgir.operators) this.cgir.operators = [];
    this.cgir.operators.push(operator);
    return this;
  }

  addIntent(intent: GeometricIntent): CGIRBuilder {
    if (!this.cgir.events) this.cgir.events = [];
    this.cgir.events.push(intent);
    return this;
  }

  // Legacy methods
  setDroplet(droplet: Droplet): CGIRBuilder {
    this.cgir.droplet = droplet;
    return this;
  }

  addNeuron(neuron: Neuron): CGIRBuilder {
    if (!this.cgir.neurons) this.cgir.neurons = [];
    this.cgir.neurons.push(neuron);
    return this;
  }

  addEvent(event: EventEntry): CGIRBuilder {
    if (!this.cgir.events) this.cgir.events = [];
    this.cgir.events.push(event);
    return this;
  }

  toJSON(): CGIR {
    return this.cgir as CGIR;
  }

  toString(): string {
    return JSON.stringify(this.toJSON(), null, 2);
  }

  /** Run geometric simulation */
  simulate(steps: number = 100, dt: number = 0.01): SimulationStep[] {
    const trajectory: SimulationStep[] = [];
    const currentState: Record<string, any> = {};

    // Initialize state
    if (this.cgir.state) {
      for (const variable of this.cgir.state) {
        currentState[variable.id] = variable.value;
      }
    }

    let currentTime = 0;

    for (let step = 0; step < steps; step++) {
      // Record current state
      trajectory.push({
        step,
        time: currentTime,
        state: { ...currentState }
      });

      // Process interactions
      if (this.cgir.interactions) {
        for (const interaction of this.cgir.interactions) {
          this.processInteraction(interaction, currentState);
        }
      }

      // Process intents at current time
      if (this.cgir.events) {
        for (const event of this.cgir.events) {
          if ('kind' in event && event.time <= currentTime) {
            this.processIntent(event, currentState);
          }
        }
      }

      currentTime += dt;
    }

    return trajectory;
  }

  private processInteraction(interaction: Interaction, state: Record<string, any>): void {
    if (interaction.kind === 'convex_mix' && interaction.space === 'oklab') {
      this.processConvexMix(interaction, state);
    }
    // Add more interaction types...
  }

  private processConvexMix(interaction: Interaction, state: Record<string, any>): void {
    const inputs = interaction.inputs;
    if (!inputs || inputs.length < 2) return;

    // Simple equal weighting for demonstration
    const weights = inputs.map(() => 1.0 / inputs.length);
    const values = inputs.map(id => state[id]).filter(v => v);

    if (values.length >= 2) {
      // For OKLab mixing, assume simple averaging
      const result = {
        L: values.reduce((sum, v) => sum + (v.L || 0), 0) / values.length,
        a: values.reduce((sum, v) => sum + (v.a || 0), 0) / values.length,
        b: values.reduce((sum, v) => sum + (v.b || 0), 0) / values.length
      };

      // Update first input as target
      state[inputs[0]] = result;
    }
  }

  private processIntent(intent: GeometricIntent, state: Record<string, any>): void {
    if (intent.kind === 'state_injection' && intent.target) {
      const value = intent.params?.value;
      if (value) {
        state[intent.target] = value;
      }
    }
    // Add more intent types...
  }

  static fromJSON(json: CGIR): CGIRBuilder {
    const builder = new CGIRBuilder(json.cgir_version);
    builder.cgir = { ...json };
    return builder;
  }
}
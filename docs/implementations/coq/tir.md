# T-IR: Typed Intermediate Representation for Coq → WASM

This document specifies the Typed Intermediate Representation (T-IR) used by the Coq → WASM compilation pipeline. T-IR is a typed, proof-aware IR that preserves enough Calculus of Inductive Constructions (CIC) structure and metadata to justify proof erasure, guide optimization, and enable sound code generation to WebAssembly.

Repository anchors
- Schema (authoritative): [docs/ir/tir-schema.json](../../ir/tir-schema.json)
- Examples: [docs/ir/examples/](../../ir/examples/) (e.g., [docs/ir/examples/minimal.json](../../ir/examples/minimal.json))
- Validator CLI: [tools/tir/validate_tir.py](../../../tools/tir/validate_tir.py)

Goals
- Preserve typing and structural evidence: inductive definitions, positivity, coverage, guarded recursion.
- Separate computational content from proof terms while recording justification metadata for erasure and DCE.
- Provide a stable JSON encoding for cross-tool interoperability and CI validation.
- Serve as the input to O-IR lowering and WASM code generation with predictable value representation.

Non-goals
- Full re-encoding of all Coq kernel internals.
- Representing all proof objects in hot-path binaries by default (they may be serialized as archives or omitted per policy).

Status
- Schema: initial version 0.1.0.
- Example(s): minimal sample available.
- Validation tool: available via Python jsonschema.

## 1. Data model overview

Top-level container
- version: semantic string (e.g., "0.1.0").
- tool: emitter identity/version (string), optional.
- module: a single module payload (see below).
- certificates: optional erasure/DCE/coverage summary emitted by passes.

Module
- name: fully-qualified identifier (e.g., "Color.Core.Algebra").
- universe_context: list of constraints (u ≤ v, etc.), optional.
- decls: sequence of global declarations.

Global declarations
- InductiveDecl
  - name, params (typed), indices (typed), constructors, positivity_cert.
- DefinitionDecl
  - name, ty (type), term (term), universe_constraints, proof_relevance flag.

Identifiers and naming
- Identifier: "^[A-Za-z_][A-Za-z0-9_'.]*$"
- Names in binders must be stable within scope; freshening is the emitter's responsibility.

Universes
- UniverseLevel: symbolic level name (string).
- UniverseConstraint: triples (lhs, rel, rhs), rel ∈ {≤, <, =, ≥, >}.

Certificates (summary)
- erasure: list of symbols and reasons (proof-irrelevant, index-only).
- dce: list of removed symbols and removal kind (binding/arg).
- coverage: per match-expression identifier, "exhaustive" or "incomplete".

## 2. Types

Kinds encoded as discriminated unions via "kind":

TyUniverse
- Universe level (e.g., Set/Typeₙ as a string level).

TyVar
- Free/de Bruijn-lifted variable by name; emitter ensures α-stable names.

TyArrow
- Non-dependent arrow A → B, encoded as a param and result (sugar over Π when non-dependent).

TyPi
- Dependent function Π x:A. B, with "dependent: true|false" (false allowed for normalized arrows).

TyInductive
- Head name with params and indices lists (types). Strict-positivity evidence recorded at the inductive declaration level.

TyApp
- Type-level application; supports fully-applied, partially-applied encodings.

Typing invariants
- Subject reduction: preserved for the pure fragment.
- Canonical forms: constructor/lambda canonical forms hold for well-typed closed values.
- Universe consistency: constraints included under module.universe_context and definition-level constraints.

## 3. Terms

Kinds:

Var
- Referenced by binder name; includes its static type.

Const
- Global constant reference; includes its static type.

Lambda
- param (name, type), body, and overall function type.

Let
- name, value (term), valueTy, body, ty, optional unfold_hint for inliner guidance.

App
- n-ary application (fn + args) with result type.

Match
- scrutinee, cases (per constructor arms with binders), resultTy, coverage_cert id/string.

Fix
- Mutually recursive group:
  - funs: list of FixFun {name, param, body, measure?, guard_cert?}
  - ty: overall type for the group’s entry function (principal type).

Construct
- Construction of an inductive value: inductive, ctor, args, ty.

Prim
- Literal constants (Int, Int64, Float, String, Bool).

Effects
- T-IR models Gallina’s pure total fragment.
- External effects (host calls) must be represented as explicit primitives or wrapper nodes in a future extension (kept out of v0.1.0).

Proof relevance flags (DefinitionDecl)
- relevant: definition produces computational content and may be used at runtime.
- proof: definition is proof-only; eligible for erasure with appropriate certificates.

## 4. Inductives and pattern matching

InductiveDecl
- params: telescope of non-index parameters (typed).
- indices: telescope of indices (typed).
- constructors: list with per-arg types.
- positivity_cert: emitter-produced evidence id (opaque string) attesting strict positivity holds.

Match
- coverage_cert: id (opaque string) bound to certificate in certificates.coverage.
- resultTy: explicit type to support preservation checks and inform codegen lowering.

Lowering notes (for later phases)
- Family indices can be erased after specialization (tracked in certificates.erasure).
- Tagging scheme for constructors is deferred to O-IR/WASM lowering; T-IR is agnostic about physical layout.

## 5. Certificates and source metadata

Erasure certificate entries
- {symbol, reason}
- Symbol refers to a globally unique name (e.g., "Color.Core.foo").

DCE certificate entries
- {symbol, kind}
- Records dead bindings/arguments eliminated post-erasure.

Coverage certificate entries
- {match_id, status}
- Links Match nodes to coverage checking outputs.

Source mapping (future extension)
- T-IR may carry spans (file:line:col) for terms/decls; omitted in v0.1.0 for compactness.
- O-IR will accumulate Coq → T-IR → O-IR spans and emit WASM custom sections.

## 6. JSON encoding constraints

- All union nodes carry a "kind" tag for reliable decoding.
- Optional fields must be omitted when not present or use schema defaults.
- Arrays default to [] when omitted (per schema "default"), but emitters are encouraged to emit explicitly for clarity.
- Stringly-typed certificates are opaque to consumers; checkers interpret them.

Versioning
- version field is mandatory at the document root.
- Backward-compatible changes are allowed by adding new "kind" cases that tools ignore by default.
- Breaking changes must bump the major version and provide converters (documented under docs/).

## 7. Validation and tooling

Validate example(s)
- From repository root:
  - python tools/tir/validate_tir.py --examples
- Validate specific file(s):
  - python tools/tir/validate_tir.py docs/ir/examples/minimal.json
- Validate from stdin:
  - cat docs/ir/examples/minimal.json | python tools/tir/validate_tir.py --stdin

Schema location
- [docs/ir/tir-schema.json](../../ir/tir-schema.json)

Validator script
- [tools/tir/validate_tir.py](../../../tools/tir/validate_tir.py)

Exit codes
- 0: all documents valid
- 1: one or more documents invalid
- 2: setup/input error

## 8. Emitter guidelines (Coq plugin)

Required behaviors
- Populate module.universe_context with all constraints in scope.
- Emit positivity_cert for each inductive (opaque id tied to a tool-internal table).
- Set DefinitionDecl.proof_relevance = "proof" for proof-only entities (Prop/Set results with erasure eligibility).
- Emit coverage_cert identifiers for each Match; coverage info may be summarized in certificates.coverage.

Naming and hygiene
- Ensure unique module-qualified symbol names for global decls.
- For binders, prefer user names where stable; otherwise generate fresh names with deterministic suffixing.

Normalization hints
- Let.unfold_hint: set true for definitions intended to guide inlining (e.g., η-short lambdas or trivial projections).

## 9. Consumer guidelines (lowering to O-IR/WASM)

- Respect proof_relevance and certificates when performing:
  - Proof erasure
  - Index erasure (dependent families)
  - DCE/inlining with justification tracking
- Preserve resultTy and typing invariants across transforms.
- Fail closed on unknown "kind" values unless explicitly downgraded by feature flags.

## 10. Examples

Minimal
- [docs/ir/examples/minimal.json](../../ir/examples/minimal.json)

Authoring new examples
- Place new examples under [docs/ir/examples/](../../ir/examples/).
- Validate with the validator and include them in CI.

## 11. Future extensions (non-normative)

- Source spans and ranges for fine-grained debugging.
- Primitive effect markers and explicit host-call terms.
- Universe polymorphism elevation: dictionary-like encodings where needed.
- Attach proof serialization stubs (content-addressed object references) for on-demand proof loading.

## 12. Contribution checklist

Before submitting:
- Valid JSON passes validation via [tools/tir/validate_tir.py](../../../tools/tir/validate_tir.py).
- Uses only schema-sanctioned fields/kinds.
- Proof relevance and universe constraints are set.
- Inductives include positivity_cert; Matches include coverage_cert.
- Include/update examples when introducing new constructs.

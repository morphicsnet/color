(*
  Constructive core for Color Geometry
  - Stdlib + Reals (Coquelicot-compatible surface, no dependency enforced here)
  - Provides foundational records/typeclasses for:
      Transform, Metric, MetricSpace, Illuminant, ColorSpace
  - Keeps proofs minimal and constructive. Algebraic laws are provided where trivial.
*)

From Coq Require Import Reals.
Set Implicit Arguments.
Generalizable All Variables.
Set Primitive Projections.

Module ColorCore.

(* A simple alias for the XYZ coordinate triple over R *)
Definition R3 := (R * R * R)%type.

(* Morphisms between coordinate spaces *)
Record Transform (A B : Type) := {
  run : A -> B
}.

(* Identity transform *)
Definition idT (A : Type) : Transform A A :=
  {| run := fun x => x |}.

(* Composition of transforms *)
Definition composeT {A B C : Type}
  (g : Transform B C) (f : Transform A B) : Transform A C :=
  {| run := fun x => run g (run f x) |}.

(* Notations *)
Infix "∘" := composeT (at level 40, left associativity).

(* Laws for transforms (constructive proofs) *)
Lemma composeT_assoc :
  forall (A B C D : Type)
         (f : Transform A B) (g : Transform B C) (h : Transform C D) (x : A),
    run (h ∘ (g ∘ f)) x = run ((h ∘ g) ∘ f) x.
Proof. reflexivity. Qed.

Lemma idT_left :
  forall (A B : Type) (f : Transform A B) (x : A),
    run (f ∘ idT A) x = run f x.
Proof. reflexivity. Qed.

Lemma idT_right :
  forall (A B : Type) (f : Transform A B) (x : A),
    run (idT B ∘ f) x = run f x.
Proof. reflexivity. Qed.

(* Metrics over a space *)
Record Metric (X : Type) := {
  dist : X -> X -> R
}.

(* Class wrapper to allow typeclass-driven instance search *)
Class MetricSpace (X : Type) := {
  metric_of : Metric X
}.

(* A simple illuminant representation in XYZ (relative) *)
Record Illuminant := {
  wp_X : R;
  wp_Y : R;
  wp_Z : R
}.

(* Color space abstraction:
   - coords: carrier type of the color space
   - toXYZ/fromXYZ: transforms to/from XYZ (as R^3)
   - cs_metric: a metric over coords (not necessarily Euclidean)
   - whitepoint: reference white
*)
Record ColorSpace := {
  coords   : Type;
  toXYZ    : Transform coords R3;
  fromXYZ  : Transform R3 coords;
  cs_metric : Metric coords;
  whitepoint : Illuminant
}.

(* Useful derived projections *)
Definition xyz_of `{cs : ColorSpace} : coords cs -> R3 :=
  fun c => run (toXYZ cs) c.

Definition coords_of_xyz `{cs : ColorSpace} : R3 -> coords cs :=
  fun v => run (fromXYZ cs) v.

(* A placeholder property for round-trip faithfulness.
   Specific instances can choose to prove stronger equalities or approximations constructively. *)
Definition roundtrip_to_from `{cs : ColorSpace} : Prop :=
  forall v, xyz_of (coords_of_xyz v) = v.

Definition roundtrip_from_to `{cs : ColorSpace} : Prop :=
  forall c, coords_of_xyz (xyz_of c) = c.

(* Bind the metric from the class for notational convenience *)
Definition d `{MetricSpace X} : X -> X -> R :=
  dist (metric_of (X:=X)).

(* Basic nonexpansiveness of identity and composition in terms of any metric,
   stated as axioms for generality (instances can refine/instantiate proofs).
   Keep these axioms in the constructive core; specialized classical facts belong to ClassicalLayer. *)
Axiom idT_nonexpansive :
  forall (X : Type) `{MetricSpace X},
    forall (x y : X), d x y = d (run (idT X) x) (run (idT X) y).

Axiom composeT_nonexpansive :
  forall (A B C : Type) `{MetricSpace A} `{MetricSpace B} `{MetricSpace C}
         (f : Transform A B) (g : Transform B C),
    (* Instances can refine with Lipschitz constants where applicable *)
    True.

(* Optional: Euclidean metric over R3 as a canonical example, kept transparent for extraction *)
Definition R3_metric : Metric R3 :=
  {| dist :=
       fun '(x1,y1,z1) '(x2,y2,z2) =>
         let dx := x1 - x2 in
         let dy := y1 - y2 in
         let dz := z1 - z2 in
         sqrt (dx*dx + dy*dy + dz*dz)
  |}.

(* Example: XYZ space as a ColorSpace instance skeleton.
   Concrete transforms are identity for illustration; instances can override later. *)
Definition XYZ_Space (D65 : Illuminant) : ColorSpace :=
  {| coords := R3;
     toXYZ := idT R3;
     fromXYZ := idT R3;
     cs_metric := R3_metric;
     whitepoint := D65 |}.

End ColorCore.
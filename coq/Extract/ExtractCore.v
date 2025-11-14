(*
  Extraction entry point for the constructive Color core.
  This produces OCaml for computationally relevant parts (e.g., transforms, metrics scaffolding).
  Policy:
    - Keep proofs opaque (not extracted).
    - Extract constructive definitions transparently.
    - Coquelicot/Real analysis is not required here; we only extract structural pieces.
*)

From Coq Require Import Reals.
From Coq Require Import extraction.Extraction.
From Coq Require Import ExtrOcamlBasic ExtrOcamlString.

From Color Require Import Core.
Module Import ColorCore.

(* Extraction configuration *)
Extraction Language OCaml.
Set Extraction AutoInline.
Set Extraction Optimize.

(* Keep Prop contents out of extracted code *)
Extract Inductive sumbool => "bool" ["true" "false"].
Extract Inductive bool => "bool" ["true" "false"].
Extract Inductive unit => "unit" ["()"].
Extract Inductive option => "option" ["Some" "None"].
Extract Inductive prod => "*(,)" [ "(,)" ].
Extract Constant sqrt => "Stdlib.sqrt".

(* Notes:
   - Coq's R (real numbers) is axiomatic; the extracted OCaml type defaults to 'float' only if remapped.
   - We intentionally do NOT remap R to float here to preserve determinism policy;
     instead, we leave R abstract (will appear as 'Obj.t' stubs) unless the user provides a concrete numeric layer.
   - For downstream performance in ocamlrun.wasm, a numeric adapter can be provided later in OCaml if desired.
*)

(* Designate computational items for extraction.
   Records and functions:
     - Transform, idT, composeT
     - Illuminant, ColorSpace (record shapes)
     - Accessors xyz_of, coords_of_xyz
     - R3_metric (structure only; 'dist' contains 'sqrt' and arithmetic on R) *)

Separate Extraction
  (* Types and records *)
  Transform
  Metric
  MetricSpace
  Illuminant
  ColorSpace

  (* Functions *)
  idT
  composeT
  xyz_of
  coords_of_xyz

  (* Example metric scaffolding *)
  R3_metric.

End ColorCore.
# End-to-end pipeline: PDF → IR → Coq → Extraction → OCaml bytecode → WASM (ocamlrun.wasm)
# Requirements:
#  - Python 3.9+ (venv)
#  - Coq 8.19/8.20 (+ coqc), dune 3.14+ (optional for coq), ocaml 5.x (optional)
#  - ocamlrun-wasm (optional for wasm run)
#
# See docs/BUILD.md for detailed instructions.

SHELL := /bin/bash

PDF_DIR := pdf
IR_DIR := build/ir
SCHEMA := docs/ir/ir-schema.json
PY := .venv/bin/python
PIP := .venv/bin/pip

# Detect tools (best-effort)
HAS_DUNE := $(shell command -v dune >/dev/null 2>&1 && echo yes || echo no)
HAS_COQC := $(shell command -v coqc >/dev/null 2>&1 && echo yes || echo no)
HAS_OCAMLWASM := $(shell command -v ocamlrun_wasm >/dev/null 2>&1 && echo yes || echo no)

.PHONY: all venv ir coq-gen coq-build extract ocaml-bytecode wasm clean

all: ir coq-gen ## Runs IR parsing and Coq generation (stops before Coq build)

venv: .venv/bin/activate
.venv/bin/activate: tools/pdf2ir/requirements.txt
	python3 -m venv .venv
	$(PIP) install -r tools/pdf2ir/requirements.txt
	@touch $@

ir: venv ## Parse PDFs into IR JSON (validated)
	$(PY) tools/pdf2ir/pdf2ir.py --in $(PDF_DIR) --out $(IR_DIR) --schema $(SCHEMA)

coq-gen: venv ir ## Generate Coq from IR (skeletons)
	$(PY) tools/ir2coq/ir2coq.py --ir $(IR_DIR) --schema $(SCHEMA)

coq-build: ## Build Coq theory (prefers dune; falls back to coqc)
ifneq ($(HAS_DUNE),no)
	dune build coq/Color/Core.vo
	dune build coq/Color/Generated/@all
	dune build coq/Extract/ExtractCore.vo
else
ifneq ($(HAS_COQC),no)
	coqc -q -R coq Color coq/Color/Core.v
	@for f in $$(ls coq/Color/Generated/*.v 2>/dev/null || true); do \
	  coqc -q -R coq Color $$f || exit 1; \
	done
	coqc -q -R coq Color coq/Extract/ExtractCore.v
else
	@echo "ERROR: Neither dune nor coqc found. Install dune-coq or Coq (coqc)." && exit 2
endif
endif

extract: coq-build ## Extract OCaml sources from Coq (Separate Extraction)
	@mkdir -p ocaml/extracted
	@(cd ocaml/extracted && coqc -q -R ../../coq Color ../../coq/Extract/ExtractCore.v) || \
	 (echo "WARN: coqc not available; skipping extraction" && exit 0)

# Minimal OCaml app scaffolding for bytecode build
ocaml/extracted/dune:
	@mkdir -p ocaml/extracted
	@echo "(library\n (name color_extracted)\n (modules :standard))" > ocaml/extracted/dune

ocaml/app/dune:
	@mkdir -p ocaml/app
	@echo "(executable\n (name main)\n (modules main)\n (libraries color_extracted)\n (modes byte))" > ocaml/app/dune

ocaml/app/main.ml:
	@mkdir -p ocaml/app
	@echo 'let () = print_endline "Color Geometry (Constructive Core) initialized"' > ocaml/app/main.ml

ocaml-bytecode: extract ocaml/extracted/dune ocaml/app/dune ocaml/app/main.ml ## Build OCaml bytecode app
ifneq ($(HAS_DUNE),no)
	dune build ocaml/app/main.bc
else
	@echo "WARN: dune not found; skipping OCaml build."
endif

wasm: ocaml-bytecode ## Run bytecode under ocamlrun-wasm (if available)
ifneq ($(HAS_OCAMLWASM),no)
	ocamlrun_wasm _build/default/ocaml/app/main.bc
else
	@echo "WARN: ocamlrun_wasm not found; skipping WASM run."
endif

clean:
	rm -rf build/ir .venv _build ocaml/extracted ocaml/app coq/Color/Generated/*.vo coq/Color/Generated/*.glob

# CGIR toolchain targets
CGIR_SCHEMA := docs/ir/cgir-schema.json

.PHONY: cgir-setup cgir-validate

cgir-setup: venv ## Install CGIR Python deps into the repo venv
	$(PIP) install -r tools/cgir/requirements.txt

cgir-validate: venv ## Validate CGIR examples against the schema
	$(PY) tools/cgir/cli_validate.py --in examples/cgir --schema $(CGIR_SCHEMA)
.PHONY: cgir-sim

cgir-sim: venv ## Run deterministic simulator on CGIR examples and write outputs to build/cgir/sim
	$(PY) tools/cgir/cli_sim.py --in examples/cgir --out build/cgir/sim --schema $(CGIR_SCHEMA) --validate --quantize-dp 12
.PHONY: cgir-viz

cgir-viz: venv ## Render OKLab droplet slice visualizations for CGIR examples
	$(PY) tools/cgir/cli_viz.py --in examples/cgir --slice-L 0.65 --out build/cgir/viz --format png --dpi 160
.PHONY: cgir-verify

# Override A and B when invoking, e.g.:
#   make cgir-verify A=build/cgir/sim B=other/run
A ?= build/cgir/sim
B ?= build/cgir/sim

cgir-verify: venv ## Compare two CGIR artifact sets for geometric equivalence
	$(PY) tools/cgir/cli_verify.py --a $(A) --b $(B) --tol 1e-12
.PHONY: cgir-train

cgir-train: venv ## Run NNLS-based attribution on CGIR examples and write outputs to build/cgir/train
	$(PY) tools/cgir/cli_train.py --in examples/cgir --out build/cgir/train --quantize-dp 12

.PHONY: cgir-test

cgir-test: venv cgir-setup ## Run pytest suite for CGIR
	$(PY) -m pytest -q tests/cgir
.PHONY: cgir-gui-setup cgir-gui cgir-gui-build

# Install GUI dependencies (PySide6, watchdog, jsonschema, matplotlib, plotly, etc.)
cgir-gui-setup: venv ## Install CGIR GUI Python deps into the repo venv
	$(PIP) install -r tools/cgir_gui/requirements.txt

# Launch CGIR Desktop GUI (runs PySide6 app)
cgir-gui: cgir-gui-setup ## Run the CGIR Desktop GUI
	$(PY) -m tools.cgir_gui.app

# Build a standalone app bundle using PyInstaller (optional; requires pyinstaller installed in venv)
cgir-gui-build: cgir-gui-setup ## Package the CGIR GUI as a standalone app (PyInstaller)
	@if ! $(PY) -m pip show pyinstaller >/dev/null 2>&1; then \
	  echo "PyInstaller not found in venv; installing..."; \
	  $(PIP) install pyinstaller; \
	fi
	$(PY) -m PyInstaller --noconfirm --clean --name "cgir-desktop" tools/cgir_gui/app.py
	@echo "Build complete. See dist/cgir-desktop/"

.PHONY: cgir-gui-test
cgir-gui-test: cgir-gui-setup ## Run GUI smoke tests
	$(PY) -m pytest -q tests/cgir_gui
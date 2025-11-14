# CGIR Desktop GUI: Unified Workspace for Color Geometry Workflows

Purpose
- Provide a cross-platform, deterministic, and intuitive desktop application that integrates all CGIR toolchain capabilities:
  - Validation
  - Simulation
  - Visualization
  - Verification
  - Training (NNLS attribution)
- Deliver a single workspace with a project explorer, real-time schema validation, interactive visualizations, side-by-side comparisons, configurable pipelines, and seamless integration with existing Makefile targets and Python CLIs.

Scope
- Architecture, UX flows, module layout, and integration specs.
- No implementation in this document; it defines the plan and acceptance criteria for development.


1) System Overview

1.1 Core Design Goals
- Determinism-first UX: all pipeline runs explicitly record versions, parameters, and output artifacts.
- Invariant semantics visualization: live OKLab droplet slicer and reachability cues to reason about states at-a-glance.
- Seamless CLI orchestration: leverage existing Python CLIs without duplicating logic.
- Robust validation: real-time JSON schema validation with actionable hints and auto-fixes where safe (e.g., ID normalization).
- Workspace-centric UX: manage project folders, examples, and artifacts with a persistent layout and state.

1.2 Runtime Stack Choice
- Primary: Python-native desktop app using PySide6 (Qt) for cross-platform performance and native feel:
  - Rationale:
    - Reuses existing Python CLIs and numeric stack directly (numpy, matplotlib, scipy, jsonschema).
    - Strong docking, tabbing, and multi-panel UX via Qt’s QDockWidget/QTabWidget.
    - Straightforward embedding of matplotlib/plotly for visualization.
    - Low overhead compared to Electron; packaging via PyInstaller brief.

- Alternative (if stakeholders prefer web stack):
  - Electron + React + TypeScript with Node spawning Python CLIs.
  - Tradeoffs: larger runtime footprint, but JS-native UI and webview-based plots.
  - Recommendation remains PySide6 to align with the current repo’s Python-centric toolchain.

1.3 High-Level Architecture (PySide6)
- Frontend (Qt/PySide6):
  - Main window with dockable panels and a central tabbed workspace.
  - Panels: Project Explorer, JSON Editor, Validation Console, Parameter Pane, Visualization Pane, Comparison Pane, Training Pane, and Status Dashboard.
  - Background workers (QThread/QProcess) for CLI task execution and logs.

- Backend (Orchestrators):
  - ProcessController: thin wrapper over subprocess/QProcess with structured IO and timeouts.
  - Validators: JSON schema validation (local via jsonschema) and semantic checks.
  - State Manager: in-memory model of loaded project files, task states, and artifacts.

- Toolchain Integration:
  - Validation: [tools/cgir/cli_validate.py](tools/cgir/cli_validate.py:1)
  - Simulation: [tools/cgir/cli_sim.py](tools/cgir/cli_sim.py:1)
  - Visualization: [tools/cgir/cli_viz.py](tools/cgir/cli_viz.py:1)
  - Verification: [tools/cgir/cli_verify.py](tools/cgir/cli_verify.py:1)
  - Training: [tools/cgir/cli_train.py](tools/cgir/cli_train.py:1)
  - Schema: [docs/ir/cgir-schema.json](docs/ir/cgir-schema.json:1)
  - Makefile: [Makefile](Makefile:90)

Mermaid: Component and IPC Overview
flowchart TD
GUI[CGIR GUI (PySide6)]:::whiteBox
Proj[Project Explorer]:::greenNode
JSONE[JSON Editor + Validator]:::greenNode
Param[Parameter Pane]:::greenNode
Viz[Live OKLab Visualization]:::greenNode
Comp[Side-by-side Verifier]:::greenNode
Train[NNLS Trainer Pane]:::greenNode
Dash[Status Dashboard]:::greenNode
PCtrl[ProcessController (QProcess)]:::blueNode
CLIs["Python CLIs (validate, sim, viz, verify, train)"]:::darkGreenNode
Make[Makefile Targets]:::pinkNode

GUI --> Proj
GUI --> JSONE
GUI --> Param
GUI --> Viz
GUI --> Comp
GUI --> Train
GUI --> Dash
GUI --> PCtrl
PCtrl --> CLIs
GUI --> Make

classDef greenNode fill:#4a7c59,stroke:#2d5236,color:#fff
classDef darkGreenNode fill:#2d5236,stroke:#1a3120,color:#fff
classDef blueNode fill:#4169e1,stroke:#2952cc,color:#fff
classDef whiteBox fill:#f5f5f5,stroke:#999,color:#333
classDef pinkNode fill:#d1477a,stroke:#b03762,color:#fff


2) UX and Interaction Design

2.1 Main Layout (Dockable)
- Left dock: Project Explorer
- Right dock: Validation Console (toggle), Status Dashboard (toggle)
- Bottom dock: Logs and Task Queue
- Center tabs:
  - Editor tabs for CGIR JSON files (Monaco-like JSON editor widget or QCodeEditor with JSON syntax & schema hints).
  - Visualization tab(s): live droplet slice with L slider and export controls.
  - Verification tab(s): side-by-side artifact comparison with tolerance slider.
  - Training tab(s): NNLS attribution runs, residual charts, and attribution tables.

2.2 Project Explorer
- Folder tree (drag-and-drop), quick filters (json/schema/errors), and example shortcuts.
- Actions:
  - New Workspace (choose folder).
  - Add Files (drag-and-drop).
  - Open Example (e.g., trace_snn_mix.json).
  - Validate All, Simulate Selected, Visualize Selected, Verify A↔B, Train Selected.
- Context menu to open in editor, run pipeline with current parameters, and open artifact folder.

2.3 JSON Editor with Real-Time Validation
- Syntax highlight, brace matching, formatting.
- Schema-bound hints using [docs/ir/cgir-schema.json](docs/ir/cgir-schema.json:1).
- Inline diagnostics (underlines), gutter markers, and quick-fix suggestions:
  - Normalize IDs to ^[a-z][a-z0-9_.-]{2,63}$.
  - Ensure weights sum per policy; propose normalize or strict_sum_1.
  - Fill missing required fields in EventEntry.
- Side panel: structured JSON outline (tree), navigate to errors.

2.4 Validation Console
- Runs [tools/cgir/cli_validate.py](tools/cgir/cli_validate.py:1) (optionally with --print-report json) for selected files or folders.
- Displays errors with anchors to file/line; double-click to focus in editor.
- Supports auto-fix for whitelist rules (ID casing/length, missing bias default 0.0).

2.5 Simulation Parameters Pane
- Controls:
  - Quantize decimals dp (default 12).
  - Schema path (default [docs/ir/cgir-schema.json](docs/ir/cgir-schema.json:1)).
  - Output directory (default build/cgir/sim).
  - Validate before simulate (toggle).
- Runs [tools/cgir/cli_sim.py](tools/cgir/cli_sim.py:1) with parameters; shows progress and opens resulting artifact.
- Surface log and deterministic summary: reachable counts, changed points, quantization policy.

2.6 Live OKLab Droplet Visualization
- Visualization tab providing:
  - L slice slider 0.0..1.0 with step 0.01.
  - Toggle overlays: neuron states, mix_raw_ok, after_projection_ok.
  - Export as PNG/SVG to build/cgir/viz/...
- Backed by [tools/cgir/cli_viz.py](tools/cgir/cli_viz.py:1) or an embedded renderer (plotly/matplotlib).
- Option: local JS renderer for instant redraw (using the same Cmax function model) while still providing “export with CLI” for reproducibility.

2.7 Side-by-side Artifact Verification
- Choose A and B (files or directories), set tolerance, run [tools/cgir/cli_verify.py](tools/cgir/cli_verify.py:1).
- Results list with status per file and per event; highlight mismatches.
- “Open both” action to compare underlying JSONs with diff highlights and numeric deltas.

2.8 Trainer (NNLS Attribution)
- Select input CGIR files; configure dp; output folder build/cgir/train.
- Run [tools/cgir/cli_train.py](tools/cgir/cli_train.py:1), render alphas (bar chart per event) and residual norms.
- Export attribution JSONs; save plots.

2.9 Status Dashboard
- Recent tasks, success/failure rates, runtime stats.
- Cards: Last Validate, Last Simulate, Last Viz Export, Last Verify, Last Train; click-through to artifacts.

2.10 Drag-and-Drop & File Browser Integration
- Drag files into Project Explorer to add.
- Built-in file chooser for input and output selections.
- “Open in Finder/Explorer” integration for artifact directories.

2.11 Multi-Tab & Layout Customization
- Multiple concurrent workflows in tabs; persistent layout serialized per workspace (JSON config).
- Dock layouts saved per user preference.

2.12 Makefile Integration
- “Run via Makefile” toggle uses:
  - cgir-validate, cgir-sim, cgir-viz, cgir-verify, cgir-train in [Makefile](Makefile:90).
- With toggle disabled, GUI calls Python CLIs directly.
- “Open Make Output” console pane and record full commands for reproducibility.


3) Technical Architecture

3.1 GUI Modules (Proposed Paths)
- tools/cgir_gui/ (new project root for GUI)
  - app.py (entrypoint; QApplication setup)
  - main_window.py (MainWindow.__init__(), dock/tab orchestration)
  - project_explorer.py (ProjectExplorerWidget.__init__())
  - json_editor.py (JsonEditorWidget.__init__(), integrates jsonschema hints)
  - validation_console.py (ValidationConsoleWidget.__init__())
  - params_panel.py (ParamsPanelWidget.__init__())
  - viz_panel.py (VizPanelWidget.__init__())
  - verify_panel.py (VerifyPanelWidget.__init__())
  - train_panel.py (TrainPanelWidget.__init__())
  - dashboard.py (DashboardWidget.__init__())
  - process_controller.py (ProcessController.run_cli_async())
  - state.py (AppState model, project/workspace states)
  - fs_watcher.py (Workspace watcher)
  - resources/ (icons, qss themes)
  - requirements.txt (PySide6, qdarkstyle/qt-material, watchdog, jsonschema, matplotlib, plotly)

Click targets:
- [tools/cgir_gui/app.py](tools/cgir_gui/app.py:1)
- [tools/cgir_gui/main_window.py](tools/cgir_gui/main_window.py:1)
- [tools/cgir_gui/project_explorer.py](tools/cgir_gui/project_explorer.py:1)
- [tools/cgir_gui/json_editor.py](tools/cgir_gui/json_editor.py:1)
- [tools/cgir_gui/validation_console.py](tools/cgir_gui/validation_console.py:1)
- [tools/cgir_gui/params_panel.py](tools/cgir_gui/params_panel.py:1)
- [tools/cgir_gui/viz_panel.py](tools/cgir_gui/viz_panel.py:1)
- [tools/cgir_gui/verify_panel.py](tools/cgir_gui/verify_panel.py:1)
- [tools/cgir_gui/train_panel.py](tools/cgir_gui/train_panel.py:1)
- [tools/cgir_gui/dashboard.py](tools/cgir_gui/dashboard.py:1)
- [tools/cgir_gui/process_controller.py](tools/cgir_gui/process_controller.py:1)
- [tools/cgir_gui/state.py](tools/cgir_gui/state.py:1)
- [tools/cgir_gui/fs_watcher.py](tools/cgir_gui/fs_watcher.py:1)
- [tools/cgir_gui/resources/](tools/cgir_gui/resources/:1)

3.2 ProcessController & CLI Protocol
- Launch child processes via QProcess/subprocess with:
  - Working directory = repo root.
  - Python path = .venv/bin/python (from Makefile vars when possible).
- Structured capture:
  - Prefer JSON output from validator (use --print-report json).
  - For other CLIs, parse stdout and link produced artifacts.
- Cancellation and timeouts:
  - Soft kill (terminate) then hard kill if not exiting within grace period.
- Deterministic run logs:
  - Save command, args, environment, timestamps, and git info (if available) in a sidecar JSON for reproducibility.

3.3 Real-Time Schema Validation
- JSON Editor runs local jsonschema validation in the UI thread or worker thread (for large files).
- Additional semantic checks replicated for instant feedback:
  - ID pattern check
  - weights_policy sum handling
  - canonical_alpha sum check
  - L bounds check
- Quick fixes propose exact edits.

3.4 Visualization Engine
- Default: call [tools/cgir/cli_viz.py](tools/cgir/cli_viz.py:1) to export PNG/SVG and render output inside the GUI.
- Optional: embedded live renderer for instant interactions:
  - Plotly (QWebEngineView) or matplotlib backend in QtAgg.
  - Same Cmax function as [tools/cgir/core/droplet.py](tools/cgir/core/droplet.py:1) for perfect alignment.

3.5 Verification UI
- Provide left/right file pickers (default to build/cgir/sim).
- Tolerance slider (1e-4 to 1e-12; default 1e-12).
- Visual diff with numeric deltas; double-click to open both JSON files in tabs.

3.6 Training UI
- Select files; choose dp, start run.
- Present attribution table per event:
  - Columns: input id, alpha, normalized alpha, residual norm.
- Provide bar charts of alpha contributions and residual norms.

3.7 Error Reporting and Suggestions
- Standardize error presentation with:
  - Title, file path, location (JSON pointer), probable cause, suggested fix.
  - One-click fix (where safe); else “apply fix in editor” suggestion.
- For process failures, present command and environment with copy button.

3.8 Build and Distribution
- Add Makefile target to run GUI:
  - cgir-gui: venv + python -m tools.cgir_gui.app
- Packaging: optional PyInstaller spec and target:
  - cgir-gui-build: produce platform-native executable bundle with resources.

Click targets to be added later:
- [Makefile](Makefile:1) → cgir-gui, cgir-gui-build

3.9 Configuration & Persistence
- Workspace config stored at .cgir/workspace.json in project root:
  - Recent files, panel layout, preferred schema, default outputs, dp settings.
- Session autosave for open tabs and unsaved JSON edits (temp buffer).

Mermaid: Key User Flows (Validation→Simulation→Visualization)
sequenceDiagram
  participant U as User
  participant E as Editor
  participant V as Validator
  participant S as Simulator
  participant Z as Visualizer

  U->>E: Open CGIR JSON
  E->>V: Trigger real-time schema validation
  V-->>E: Diagnostics + suggestions
  U->>S: Run simulate with params (dp, output dir, validate=true)
  S-->>U: Progress + success; artifacts written
  U->>Z: Visualize L-slice (e.g., 0.65)
  Z-->>U: Render overlays and export PNG/SVG


4) Mapping UI Actions to Existing Toolchain

- Validate:
  - Command: [tools/cgir/cli_validate.py](tools/cgir/cli_validate.py:1) --in PATH --schema docs/ir/cgir-schema.json --print-report json
- Simulate:
  - Command: [tools/cgir/cli_sim.py](tools/cgir/cli_sim.py:1) --in PATH --out PATH --schema docs/ir/cgir-schema.json --validate --quantize-dp DP
- Visualize:
  - Command: [tools/cgir/cli_viz.py](tools/cgir/cli_viz.py:1) --in FILE|DIR --slice-L LVAL --out PATH --format png|svg --dpi 160
- Verify:
  - Command: [tools/cgir/cli_verify.py](tools/cgir/cli_verify.py:1) --a PATH --b PATH --tol EPS
- Train:
  - Command: [tools/cgir/cli_train.py](tools/cgir/cli_train.py:1) --in PATH --out PATH --quantize-dp DP
- Makefile-driven alternative:
  - Targets: cgir-validate, cgir-sim, cgir-viz, cgir-verify, cgir-train in [Makefile](Makefile:90)


5) Accessibility, Performance, and Security

5.1 Accessibility
- Keyboard-first navigation; shortcuts for validate/simulate/visualize/verify/train.
- High-contrast theme support (Qt stylesheets), scalable fonts.

5.2 Performance
- Use process pools for parallel validations (with concurrency limits).
- Stream logs incrementally and parse lazily for large projects.

5.3 Security
- Explicit prompt before running external commands or writing artifacts.
- Sanitize file paths and treat JSON parsing exceptions gracefully.
- All subprocess env settings are whitelisted and logged.

5.4 Reproducibility
- Every operation stamps: tool versions, CLI command-line, schema ID, dp, outputs.
- Provide a “copy repro script” feature that prints the exact commands executed.


6) Deliverables and File Layout

6.1 New GUI Project Skeleton (no implementation here, just proposed structure)
- [tools/cgir_gui/app.py](tools/cgir_gui/app.py:1) — application bootstrap
- [tools/cgir_gui/main_window.py](tools/cgir_gui/main_window.py:1) — main window docking/tabs
- [tools/cgir_gui/project_explorer.py](tools/cgir_gui/project_explorer.py:1) — project tree + actions
- [tools/cgir_gui/json_editor.py](tools/cgir_gui/json_editor.py:1) — schema-bound JSON editor
- [tools/cgir_gui/validation_console.py](tools/cgir_gui/validation_console.py:1) — diagnostics panel
- [tools/cgir_gui/params_panel.py](tools/cgir_gui/params_panel.py:1) — simulation/visualization params
- [tools/cgir_gui/viz_panel.py](tools/cgir_gui/viz_panel.py:1) — live droplet visualization
- [tools/cgir_gui/verify_panel.py](tools/cgir_gui/verify_panel.py:1) — side-by-side comparison
- [tools/cgir_gui/train_panel.py](tools/cgir_gui/train_panel.py:1) — NNLS attribution UI
- [tools/cgir_gui/dashboard.py](tools/cgir_gui/dashboard.py:1) — status dashboard
- [tools/cgir_gui/process_controller.py](tools/cgir_gui/process_controller.py:1) — CLI orchestration
- [tools/cgir_gui/state.py](tools/cgir_gui/state.py:1) — app/workspace state
- [tools/cgir_gui/fs_watcher.py](tools/cgir_gui/fs_watcher.py:1) — filesystem watching
- [tools/cgir_gui/resources/](tools/cgir_gui/resources/:1) — icons, themes

6.2 Dependencies (to add in a GUI-specific requirements file)
- PySide6
- watchdog
- jsonschema
- matplotlib
- plotly
- qdarkstyle or qt-material
- (Optional) qtwebengine for plotly-based webviews
- pydantic (for config modeling)
- rich (for pretty logs)

6.3 Makefile Additions (Design Only)
- cgir-gui: run the GUI app in venv.
- cgir-gui-build: package the GUI with PyInstaller for macOS/Linux/Windows.


7) Acceptance Criteria

- Project Explorer:
  - Drag-and-drop adds files; operations reflected immediately.
  - Filters and quick actions (validate, simulate, visualize, verify, train) work on selection.

- JSON Editor:
  - Real-time validation against [docs/ir/cgir-schema.json](docs/ir/cgir-schema.json:1); errors are highlighted and navigable.
  - “Apply quick fix” updates JSON in place for safe transformations.

- Simulation:
  - Adjust dp, schema path, and output directory; run produces artifacts and populates Results.
  - Status shows counts for reachable vs non-reachable; artifacts openable from UI.

- Visualization:
  - Live OKLab droplet slice updates as L slider moves; overlays toggled; export works (PNG/SVG).

- Verification:
  - Side-by-side comparison returns OK/FAILED with details; mismatches link to file diff.

- Training:
  - Trainer runs NNLS, shows alphas/residuals, and exports attribution JSONs.

- Dashboard:
  - Shows last run status, durations, and present artifacts; all links functional.

- Makefile Integration:
  - Toggle to use Make targets instead of direct CLIs; logs preserved.

- Persistence:
  - Reopening the app restores the last workspace layout and open tabs.

- Error Handling:
  - All subprocess errors reported with actionable hints; schema errors include pointers.

- Reproducibility:
  - “Copy repro script” yields complete command lines for any pipeline run with identical parameters.

- Cross-Platform:
  - App runs on macOS, Linux, Windows with identical functionality (subject to packaging).



Appendix A: Mapping to Current Repository

- Uses current CLIs:
  - [tools/cgir/cli_validate.py](tools/cgir/cli_validate.py:1)
  - [tools/cgir/cli_sim.py](tools/cgir/cli_sim.py:1)
  - [tools/cgir/cli_viz.py](tools/cgir/cli_viz.py:1)
  - [tools/cgir/cli_verify.py](tools/cgir/cli_verify.py:1)
  - [tools/cgir/cli_train.py](tools/cgir/cli_train.py:1)

- Schema:
  - [docs/ir/cgir-schema.json](docs/ir/cgir-schema.json:1)

- Makefile targets:
  - [Makefile](Makefile:90) cgir-setup, cgir-validate, cgir-sim, cgir-viz, cgir-verify, cgir-train



Appendix B: Phased Delivery Plan

Phase 1: Shell + Validation
- Create GUI skeleton with Project Explorer, JSON Editor, Validation Console, and run cgir-validate.
- Wire real-time schema validation locally.

Phase 2: Simulation + Visualization
- Integrate parameter pane, run cgir-sim, and visualize generated artifacts.
- Add live L-slice view (initially backed by CLI exports).

Phase 3: Verification + Training
- Implement comparison panel (cgir-verify).
- Implement trainer panel (cgir-train) with attribution charts.

Phase 4: Makefile + Packaging
- Add cgir-gui, cgir-gui-build targets and package GUI.

Phase 5: Polish + Docs
- Shortcuts, themes, persistent layouts, and documentation pages.



Appendix C: Future Enhancements
- Multi-run result matrices (various dp values) and Pareto views for residual vs determinism.
- Integrated Coq stubs preview after ir2coq updates for CGIR IR.
- Workspace templates and wizards for new projects.
- Headless batch GUI mode for CI artifact staging.

8) Component Reference

8.1 Dashboard
- Shows project root, examples path, build artifacts path.
- Real-time stats:
  - Count of example JSONs (recursive).
  - Count of simulated artifacts under build/cgir/sim.
  - Last run metadata (task, exit code, timestamp) sourced from .cgir/runs/*.json.
- Quick actions to open paths in Finder/Explorer.
- Recent files list; activates editor on selection.

8.2 JSON Editor
- Real-time JSON parsing and schema validation (Draft 2020-12).
- Actions: Save, Save As, Format (pretty-print), Set as Default Schema (persists to .cgir/workspace.json).
- Diagnostics list with debounced validation.
- Accessibility: sets accessible names for editor and diagnostics list.

8.3 Process Controller
- QProcess-based runner with:
  - Merged stdout/stderr streaming via output signal.
  - Timeout support with polite terminate then hard kill after grace.
  - Structured reproducibility capture in .cgir/runs/*.json.
  - Streaming log file in .cgir/logs/*.log.
  - Signals: started, output, finished, error, timeout.

8.4 Preferences and Persistence
- Stored in .cgir/workspace.json (schema path, dp, out_dir, last_opened_dir, recents, panel layout).
- Updated automatically when:
  - Changing parameters in the Parameters panel.
  - Opening a new workspace directory.
  - Opening a file in the editor.

9) Testing

- Run GUI smoke tests:
  - make cgir-gui-test
- Test scope (tests/cgir_gui/test_smoke.py):
  - Headless QApplication startup (QT_QPA_PLATFORM=offscreen).
  - Instantiate MainWindow and basic panels without errors.
  - ProcessController runs a trivial Python command and returns exit code 0.

## GUI Test Plan

### Smoke Test Coverage

| Component | Test File | Test Coverage |
|-----------|-----------|---------------|
| MainWindow | `tests/cgir_gui/test_smoke.py` | Init, basic panel instantiation, no crashes |
| ProcessController | `tests/cgir_gui/test_smoke.py` | Run trivial Python command, exit code 0 |
| Dashboard | `tests/cgir_gui/test_dashboard_smoke.py` | Stats computation (examples count, sim count), last run text presence |
| Project Explorer | `tests/cgir_gui/test_project_explorer.py` | Set root directory, filter functionality |

### Manual Test Checklist

#### Interactive Panel Workflows
**Validate Panel:**
1. Open Project Explorer → right-click CGIR file → Validate
2. Expected: validation results in console, errors highlighted
3. Artifacts: `.cgir/runs/*.json` logs, console output

**Simulate Panel:**
1. Menu → Simulate → Select file → Set dp parameter → Run
2. Expected: progress indicator, success notification
3. Artifacts: `build/cgir/sim/*.json` outputs

**Visualize Panel:**
1. Menu → Visualize → Select simulation artifact → Set L-slice → Export
2. Expected: OKLab droplet rendering, PNG/SVG export
3. Artifacts: `build/cgir/viz/*.png|*.svg` files

**Verify Panel:**
1. Menu → Verify → Select two artifacts → Set tolerance → Compare
2. Expected: side-by-side comparison, mismatch highlights
3. Artifacts: verification report, diff highlighting

**Train Panel:**
1. Menu → Train → Select CGIR files → Set dp → Run NNLS
2. Expected: attribution charts, residual norms display
3. Artifacts: `build/cgir/train/*_attrib.json` files

#### Theme Validation
- Test dark theme: `CGIR_THEME=dark make cgir-gui`
- Test light theme: `CGIR_THEME=light make cgir-gui`
- Test default (no theme): `make cgir-gui`
- Expected: proper color scheme application, no style crashes

### Headless CI Testing

Run automated tests without display:
```bash
QT_QPA_PLATFORM=offscreen make cgir-gui-test
```

Expected output: All smoke tests pass, no GUI windows appear, suitable for CI/CD pipelines.

### Test Execution Commands

- Full GUI test suite: `make cgir-gui-test`
- Individual test files:
  - `python -m pytest tests/cgir_gui/test_smoke.py -v`
  - `python -m pytest tests/cgir_gui/test_dashboard_smoke.py -v`
  - `python -m pytest tests/cgir_gui/test_project_explorer.py -v`

10) Performance and Accessibility Notes

- Visualization subsamples off-slice overlays for large datasets to keep rendering interactive.
- Keyboard shortcuts:
  - Open File: Ctrl+O
  - Open Folder: Ctrl+Shift+O
  - Open in Editor: Ctrl+E
  - Validate: F5
  - Simulate: Ctrl+R
  - Visualize: Ctrl+Shift+V
  - Verify: Ctrl+Shift+C
  - Train: Ctrl+T
  - Stop Process: Esc
- High-contrast themes can be applied with qdarkstyle; consider additional QSS for enhanced contrast as needed.


11) Themes

- Optional QSS themes can be applied via the CGIR_THEME environment variable.
  - Set CGIR_THEME=dark to apply [tools/cgir_gui/resources/dark.qss](tools/cgir_gui/resources/dark.qss:1).
  - Set CGIR_THEME=light to apply [tools/cgir_gui/resources/light.qss](tools/cgir_gui/resources/light.qss:1).
  - Theme resources live under [tools/cgir_gui/resources/](tools/cgir_gui/resources/:1).

- Default behavior:
  - If CGIR_THEME is not set or the QSS file is missing, the application uses the native style without crashing.
  - Existing qdarkstyle package remains available for future use but is not required.

- Examples:
  - $ CGIR_THEME=dark make cgir-gui
  - $ CGIR_THEME=light make cgir-gui
  - $ make cgir-gui  (native style)

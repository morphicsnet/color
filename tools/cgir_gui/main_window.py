# pylint: disable=import-error,no-name-in-module

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QProcess, QSize, QDir
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QDockWidget,
    QTreeView,
    QFileSystemModel,
    QTextEdit,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QLabel,
    QFileDialog,
    QToolBar,
    QStatusBar,
    QMessageBox,
    QSplitter,
    QSizePolicy,
    QCheckBox,
)
from .json_editor import JsonEditorWidget
from .process_controller import ProcessController
from .dashboard import DashboardWidget
from .state import load_workspace, save_workspace, update_params, update_last_opened
from .fs_watcher import FSWatcher
from .project_explorer import ProjectExplorer


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def venv_python() -> str:
    # Use the repo's venv if present, else current interpreter
    root = repo_root()
    cand = root / ".venv" / "bin" / "python"
    if cand.exists():
        return str(cand)
    return sys.executable


def default_schema() -> str:
    return str(repo_root() / "docs" / "ir" / "cgir-schema.json")


def default_examples_dir() -> str:
    return str(repo_root() / "examples" / "cgir")


def default_build_dir() -> str:
    return str(repo_root() / "build" / "cgir")




class ParamsPanel(QWidget):
    def __init__(self, parent: QMainWindow) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout()
        self.edit_schema = QLineEdit(default_schema())
        self.btn_schema = QPushButton("Browse…")
        self.btn_schema.clicked.connect(self._choose_schema)

        hl1 = QHBoxLayout()
        hl1.addWidget(self.edit_schema)
        hl1.addWidget(self.btn_schema)

        self.spin_dp = QSpinBox()
        self.spin_dp.setRange(0, 16)
        self.spin_dp.setValue(12)

        self.edit_out = QLineEdit(default_build_dir())
        self.btn_out = QPushButton("Browse…")
        self.btn_out.clicked.connect(self._choose_out_dir)

        hl2 = QHBoxLayout()
        hl2.addWidget(self.edit_out)
        hl2.addWidget(self.btn_out)

        self.check_validate_before = QCheckBox("Validate before simulate")
        self.check_validate_before.setChecked(True)

        form.addRow("Schema:", QWidget())
        form.addRow(hl1)
        form.addRow("Quantize dp:", self.spin_dp)
        form.addRow("Output dir:", QWidget())
        form.addRow(hl2)
        form.addRow(self.check_validate_before)

        self.setLayout(form)

    def _choose_schema(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Choose Schema", default_schema(), "JSON (*.json)")
        if p:
            self.edit_schema.setText(p)

    def _choose_out_dir(self) -> None:
        p = QFileDialog.getExistingDirectory(self, "Choose Output Directory", default_build_dir())
        if p:
            self.edit_out.setText(p)

    def params(self) -> dict:
        return {
            "schema": self.edit_schema.text().strip(),
            "dp": self.spin_dp.value(),
            "out": self.edit_out.text().strip(),
            "validate": self.check_validate_before.isChecked(),
        }



class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CGIR Desktop")
        self.resize(1200, 800)
        self._init_state()
        self._create_widgets()
        self._create_actions()
        self._create_menu_and_toolbar()
        self._wire_defaults()

    def _init_state(self) -> None:
        self.python = venv_python()
        self.root = repo_root()
        # Load workspace preferences
        self._ws = load_workspace()
        self.schema_path = self._ws.params.schema
        self.proc = ProcessController(self)
        self.current_file: Optional[Path] = None

    def _create_widgets(self) -> None:
        # Central tabs
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        # Welcome tab
        welcome = QTextEdit(self)
        welcome.setReadOnly(True)
        welcome.setHtml(
            "<h2>CGIR Desktop</h2>"
            "<p>Unified workspace for validation, simulation, visualization, verification, and training.</p>"
            "<p>Select files in the Project Explorer and use the toolbar actions.</p>"
        )
        self.tabs.addTab(welcome, "Welcome")
        # Dashboard tab
        self.dashboard = DashboardWidget(self, on_open_file=self.open_in_editor)
        self.tabs.addTab(self.dashboard, "Dashboard")

        # Dock: Project Explorer
        self.explorer = ProjectExplorer(self)
        dock_left = QDockWidget("Project Explorer", self)
        dock_left.setWidget(self.explorer)
        dock_left.setObjectName("dock_project_explorer")
        dock_left.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock_left)

        # Dock: Validation Console
        self.validation_console = QTextEdit(self)
        self.validation_console.setReadOnly(True)
        dock_right = QDockWidget("Validation Console", self)
        dock_right.setWidget(self.validation_console)
        dock_right.setObjectName("dock_validation_console")
        dock_right.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_right)

        # Bottom: Logs
        self.logs = QTextEdit(self)
        self.logs.setReadOnly(True)
        dock_bottom = QDockWidget("Logs", self)
        dock_bottom.setWidget(self.logs)
        dock_bottom.setObjectName("dock_logs")
        dock_bottom.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock_bottom)

        # Dock: Parameters
        self.params_panel = ParamsPanel(self)
        dock_params = QDockWidget("Parameters", self)
        dock_params.setWidget(self.params_panel)
        dock_params.setObjectName("dock_params")
        dock_params.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_params)

        # Apply preferences to UI and bind change signals
        self._apply_prefs_to_ui()
        self.params_panel.spin_dp.valueChanged.connect(lambda _v: self._update_ws_params())
        self.params_panel.edit_schema.editingFinished.connect(self._update_ws_params)
        self.params_panel.edit_out.editingFinished.connect(self._update_ws_params)

        # Now that logs exists, attach to process controller
        self.proc.log_sink = self.logs

        # Status bar
        self.setStatusBar(QStatusBar(self))

        # Wire process signals to logs
        self.proc.started.connect(lambda s: self.logs.append(f"$ {s}\n"))
        self.proc.output.connect(lambda t: self.logs.insertPlainText(t))
        self.proc.finished.connect(lambda res: self.logs.append(f"\n[exit code: {res.exit_code}]\n"))
        self.proc.error.connect(lambda e: self.logs.append(f"[error] {e}\n"))
        try:
            self.proc.timeout.connect(lambda: self.logs.append("[timeout] Process exceeded timeout\n"))
        except Exception:
            pass

        # Filesystem watcher: auto-refresh Dashboard on workspace/artifacts changes
        try:
            self.fs = FSWatcher(self)
            self.fs.watch([repo_root() / ".cgir", Path(default_examples_dir()), Path(default_build_dir())])
            self.fs.changed.connect(lambda _p: self.dashboard.refresh())
        except Exception:
            pass

    def _create_actions(self) -> None:
        self.act_open_file = QAction("Open File…", self)
        self.act_open_file.triggered.connect(self.open_file_dialog)

        self.act_open_dir = QAction("Open Folder…", self)
        self.act_open_dir.triggered.connect(self.open_folder_dialog)

        self.act_open_in_editor = QAction("Open in Editor", self)
        self.act_open_in_editor.triggered.connect(self.open_in_editor_selected)

        self.act_validate = QAction("Validate", self)
        self.act_validate.triggered.connect(self.run_validate)

        self.act_simulate = QAction("Simulate", self)
        self.act_simulate.triggered.connect(self.run_simulate)

        self.act_visualize = QAction("Visualize", self)
        self.act_visualize.triggered.connect(self.run_visualize)

        self.act_verify = QAction("Verify A↔B", self)
        self.act_verify.triggered.connect(self.run_verify_dialog)

        self.act_train = QAction("Train (NNLS)", self)
        self.act_train.triggered.connect(self.run_train)

        self.act_stop = QAction("Stop Process", self)
        self.act_stop.triggered.connect(self.proc.terminate)

        self.act_quit = QAction("Quit", self)
        self.act_quit.triggered.connect(self.close)

        # View actions
        self.act_show_dashboard = QAction("Show Dashboard", self)
        self.act_show_dashboard.triggered.connect(self.show_dashboard)

        # Accessibility: keyboard shortcuts
        self.act_open_file.setShortcut("Ctrl+O")
        self.act_open_dir.setShortcut("Ctrl+Shift+O")
        self.act_open_in_editor.setShortcut("Ctrl+E")
        self.act_validate.setShortcut("F5")
        self.act_simulate.setShortcut("Ctrl+R")
        self.act_visualize.setShortcut("Ctrl+Shift+V")
        self.act_verify.setShortcut("Ctrl+Shift+C")
        self.act_train.setShortcut("Ctrl+T")
        self.act_stop.setShortcut("Esc")

        # Shortcuts
        self.act_open_file.setShortcut("Ctrl+O")
        self.act_open_dir.setShortcut("Ctrl+Shift+O")
        self.act_open_in_editor.setShortcut("Ctrl+E")
        self.act_validate.setShortcut("F5")
        self.act_simulate.setShortcut("Ctrl+R")
        self.act_visualize.setShortcut("Ctrl+Shift+V")
        self.act_verify.setShortcut("Ctrl+Shift+C")
        self.act_train.setShortcut("Ctrl+T")
        self.act_stop.setShortcut("Esc")

    def _create_menu_and_toolbar(self) -> None:
        # Menu
        menu_file = self.menuBar().addMenu("&File")
        menu_file.addAction(self.act_open_file)
        menu_file.addAction(self.act_open_dir)
        menu_file.addAction(self.act_open_in_editor)
        menu_file.addSeparator()
        menu_file.addAction(self.act_quit)

        menu_run = self.menuBar().addMenu("&Run")
        for a in (self.act_validate, self.act_simulate, self.act_visualize, self.act_verify, self.act_train, self.act_stop):
            menu_run.addAction(a)

        menu_view = self.menuBar().addMenu("&View")
        menu_view.addAction(self.act_show_dashboard)

        # Toolbar
        tb = QToolBar("Main")
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)
        for a in (self.act_open_file, self.act_open_dir, self.act_open_in_editor, self.act_show_dashboard, self.act_validate, self.act_simulate, self.act_visualize, self.act_verify, self.act_train, self.act_stop):
            tb.addAction(a)

    def _wire_defaults(self) -> None:
        # Try to default selection to examples/cgir
        self.statusBar().showMessage(str(default_examples_dir()))
        # Ensure build dir exists
        Path(default_build_dir()).mkdir(parents=True, exist_ok=True)

    # ----------------------------
    # Helpers
    # ----------------------------
    def _selected_path_or_examples(self) -> Path:
        sel = self.explorer.selected_path()
        if sel is not None:
            return sel
        return Path(default_examples_dir())

    def _tools_path(self, rel: str) -> str:
        return str(self.root / rel)

    # ----------------------------
    # File/Folder actions
    # ----------------------------
    def open_file_dialog(self) -> None:
        p, _ = QFileDialog.getOpenFileName(
            self,
            "Open CGIR JSON",
            default_examples_dir(),
            "JSON (*.json)"
        )
        if not p:
            return
        self.open_in_editor(Path(p))

    def open_folder_dialog(self) -> None:
        p = QFileDialog.getExistingDirectory(self, "Open Workspace", default_examples_dir())
        if not p:
            return
        self.explorer.set_root(p)
        self.statusBar().showMessage(p)
        # Persist preference
        try:
            self._ws = update_last_opened(self._ws, directory=p)
            save_workspace(self._ws)
        except Exception:
            pass

    def open_in_editor_selected(self) -> None:
        sel = self._selected_path_or_examples()
        if sel.is_file():
            self.open_in_editor(sel)
        else:
            QMessageBox.information(self, "Open in Editor", "Select a JSON file in the Project Explorer.")

    def open_in_editor(self, path: Path) -> None:
        try:
            editor = JsonEditorWidget(self, schema_path=default_schema())
            editor.load_file(path)
            self.tabs.addTab(editor, path.name)
            self.tabs.setCurrentWidget(editor)
            self.statusBar().showMessage(str(path))
            # Update workspace recents
            try:
                self._ws = update_last_opened(self._ws, file=str(path))
                save_workspace(self._ws)
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "Open in Editor Error", f"{path}: {e}")

    # ----------------------------
    # Run: Validate
    # ----------------------------
    def run_validate(self) -> None:
        target = self._selected_path_or_examples()
        schema = self.params_panel.params()["schema"]
        cmd = [
            self.python,
            self._tools_path("tools/cgir/cli_validate.py"),
            "--in", str(target),
            "--schema", schema,
            "--print-report", "text",
        ]
        metadata = {"task": "validate", "target": str(target), "schema": schema}
        self.proc.run(cmd, workdir=self.root, metadata=metadata)

    # ----------------------------
    # Run: Simulate
    # ----------------------------
    def run_simulate(self) -> None:
        target = self._selected_path_or_examples()
        params = self.params_panel.params()
        out_dir = params["out"]
        dp = params["dp"]
        schema = params["schema"]
        cmd = [
            self.python,
            self._tools_path("tools/cgir/cli_sim.py"),
            "--in", str(target),
            "--out", str(out_dir),
            "--schema", schema,
            "--quantize-dp", str(dp),
        ]
        if params["validate"]:
            cmd.append("--validate")
        metadata = {
            "task": "simulate",
            "target": str(target),
            "out": str(out_dir),
            "schema": schema,
            "dp": dp,
            "validate": bool(params["validate"]),
        }
        self.proc.run(cmd, workdir=self.root, metadata=metadata)

    # ----------------------------
    # Run: Visualize (OKLab slice)
    # ----------------------------
    def run_visualize(self) -> None:
        target = self._selected_path_or_examples()
        params = self.params_panel.params()
        out_dir = Path(default_build_dir()) / "viz"
        out_dir.mkdir(parents=True, exist_ok=True)
        # Default L slice; later wire to a UI slider/input
        L = 0.65
        cmd = [
            self.python,
            self._tools_path("tools/cgir/cli_viz.py"),
            "--in", str(target),
            "--slice-L", str(L),
            "--out", str(out_dir),
            "--format", "png",
            "--dpi", "160",
        ]
        metadata = {"task": "visualize", "target": str(target), "slice_L": L, "out": str(out_dir)}
        self.proc.run(cmd, workdir=self.root, metadata=metadata)

    # ----------------------------
    # Preferences (workspace)
    # ----------------------------
    def _apply_prefs_to_ui(self) -> None:
        try:
            p = self._ws.params
            self.params_panel.edit_schema.setText(str(p.schema))
            self.params_panel.spin_dp.setValue(int(p.dp))
            self.params_panel.edit_out.setText(str(p.out_dir))
        except Exception:
            # Non-fatal
            pass

    def _update_ws_params(self) -> None:
        try:
            self._ws = update_params(
                self._ws,
                schema=self.params_panel.edit_schema.text().strip(),
                dp=int(self.params_panel.spin_dp.value()),
                out_dir=self.params_panel.edit_out.text().strip(),
            )
            save_workspace(self._ws)
        except Exception:
            # Non-fatal
            pass

    def closeEvent(self, event) -> None:
        try:
            save_workspace(self._ws)
        except Exception:
            pass
        super().closeEvent(event)

    # ----------------------------
    # Run: Verify A↔B
    # ----------------------------
    def run_verify_dialog(self) -> None:
        A = QFileDialog.getExistingDirectory(self, "Choose Artifact Directory A", str(Path(default_build_dir()) / "sim"))
        if not A:
            return
        B = QFileDialog.getExistingDirectory(self, "Choose Artifact Directory B", str(Path(default_build_dir()) / "sim"))
        if not B:
            return
        cmd = [
            self.python,
            self._tools_path("tools/cgir/cli_verify.py"),
            "--a", A,
            "--b", B,
            "--tol", "1e-12",
        ]
        metadata = {"task": "verify", "A": A, "B": B, "tol": 1e-12}
        self.proc.run(cmd, workdir=self.root, metadata=metadata)

    def show_dashboard(self) -> None:
        try:
            idx = self.tabs.indexOf(self.dashboard)
            if idx != -1:
                self.tabs.setCurrentIndex(idx)
        except Exception:
            # Non-fatal if dashboard not yet constructed
            pass

    # ----------------------------
    # Run: Train (NNLS)
    # ----------------------------
    def run_train(self) -> None:
        target = self._selected_path_or_examples()
        out_dir = Path(default_build_dir()) / "train"
        out_dir.mkdir(parents=True, exist_ok=True)
        dp = self.params_panel.params()["dp"]
        cmd = [
            self.python,
            self._tools_path("tools/cgir/cli_train.py"),
            "--in", str(target),
            "--out", str(out_dir),
            "--quantize-dp", str(dp),
        ]
        metadata = {"task": "train", "target": str(target), "out": str(out_dir), "dp": dp}
        self.proc.run(cmd, workdir=self.root, metadata=metadata)
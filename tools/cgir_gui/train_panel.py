# pylint: disable=import-error,no-name-in-module

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QFileDialog,
    QSpinBox,
    QTextEdit,
    QMessageBox,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QCheckBox,
    QComboBox,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .process_controller import ProcessController


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def venv_python() -> str:
    root = repo_root()
    cand = root / ".venv" / "bin" / "python"
    return str(cand) if cand.exists() else "python3"


def default_examples_dir() -> str:
    return str(repo_root() / "examples" / "cgir")


def default_train_dir() -> str:
    return str(repo_root() / "build" / "cgir" / "train")


@dataclass
class AttribEvent:
    index: int
    target_ok: Tuple[float, float, float]
    alphas: List[Tuple[str, float]]
    residual_norm: float
    sum_alpha_before_norm: float
    normalized: bool
    error: Optional[str] = None


class TrainPanel(QWidget):
    """
    NNLS Attribution Trainer Panel (CGIR).

    Features:
      - Choose CGIR file or directory
      - Choose output dir (default: build/cgir/train)
      - dp (quantize decimals)
      - Run training via tools/cgir/cli_train.py
      - Display results:
          * file selector for produced _attrib.json (when input is a dir)
          * per-event table (index, residual_norm, normalized, sum_alpha_before_norm)
          * bar chart of alpha contributions for selected event
      - Console shows process stdout/stderr; exit code on finish

    Emits:
      - finished(int): exit code (0 OK, nonzero failure)
    """

    finished = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._proc = ProcessController(self)
        self._proc.started.connect(lambda s: self._append_log(f"$ {s}\n"))
        self._proc.output.connect(self._append_log)
        self._proc.finished.connect(self._on_finished)
        self._proc.error.connect(lambda e: self._append_log(f"[error] {e}\n"))

        self._build_ui()

        # State
        self._last_input: Optional[Path] = None
        self._last_out_dir: Optional[Path] = None
        self._attrib_files: List[Path] = []
        self._events: List[AttribEvent] = []

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Controls
        form = QFormLayout()

        self.edit_input = QLineEdit(default_examples_dir())
        btn_in = QPushButton("Browse…")
        btn_in.clicked.connect(self._choose_input)
        row_in = QHBoxLayout()
        row_in.addWidget(self.edit_input, stretch=1)
        row_in.addWidget(btn_in)

        self.edit_out = QLineEdit(default_train_dir())
        btn_out = QPushButton("Browse…")
        btn_out.clicked.connect(self._choose_out)
        row_out = QHBoxLayout()
        row_out.addWidget(self.edit_out, stretch=1)
        row_out.addWidget(btn_out)

        self.spin_dp = QSpinBox()
        self.spin_dp.setRange(0, 16)
        self.spin_dp.setValue(12)

        self.chk_use_make = QCheckBox("Use Makefile target (cgir-train)")
        self.btn_run = QPushButton("Run Training")
        self.btn_run.clicked.connect(self.run_train)

        row_ctrl = QHBoxLayout()
        row_ctrl.addWidget(self.chk_use_make)
        row_ctrl.addStretch()
        row_ctrl.addWidget(self.btn_run)

        form.addRow("Input (file or directory):", QWidget())
        form.addRow(row_in)
        form.addRow("Output directory:", QWidget())
        form.addRow(row_out)
        form.addRow("Quantize dp:", self.spin_dp)
        form.addRow(row_ctrl)

        root.addLayout(form)

        # Splitter: Left (table) / Right (chart)
        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Horizontal)

        # Left container (file chooser for attrib JSON + table + console)
        left = QVBoxLayout()
        leftw = QWidget(self)
        leftw.setLayout(left)

        row_files = QHBoxLayout()
        self.combo_files = QComboBox(self)
        self.combo_files.currentIndexChanged.connect(self._on_choose_attrib_file)
        btn_refresh = QPushButton("Refresh Results")
        btn_refresh.clicked.connect(self.refresh_results)
        row_files.addWidget(QLabel("Attribution file:"))
        row_files.addWidget(self.combo_files, stretch=1)
        row_files.addWidget(btn_refresh)

        left.addLayout(row_files)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["event_index", "residual_norm", "normalized", "sum_alpha_before_norm"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        left.addWidget(self.table, stretch=1)

        self.console = QTextEdit(self)
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QTextEdit.NoWrap)
        left.addWidget(self.console, stretch=0)

        splitter.addWidget(leftw)

        # Right container (bar chart)
        right = QVBoxLayout()
        rightw = QWidget(self)
        rightw.setLayout(right)

        self.figure = Figure(figsize=(6.0, 4.0), dpi=150)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right.addWidget(QLabel("Alpha contributions (selected event)"))
        right.addWidget(self.canvas, stretch=1)

        splitter.addWidget(rightw)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        root.addWidget(splitter, stretch=1)

    # -------------------------
    # UI Callbacks
    # -------------------------
    def _choose_input(self) -> None:
        base = self.edit_input.text().strip() or default_examples_dir()
        # Offer both file and directory selection
        # Try file first
        p, _ = QFileDialog.getOpenFileName(self, "Choose CGIR JSON file", base, "JSON (*.json)")
        if p:
            self.edit_input.setText(p)
            return
        d = QFileDialog.getExistingDirectory(self, "Choose input directory", base)
        if d:
            self.edit_input.setText(d)

    def _choose_out(self) -> None:
        base = self.edit_out.text().strip() or default_train_dir()
        d = QFileDialog.getExistingDirectory(self, "Choose output directory", base)
        if d:
            self.edit_out.setText(d)

    def run_train(self) -> None:
        inp = Path(self.edit_input.text().strip())
        out_dir = Path(self.edit_out.text().strip())
        dp = self.spin_dp.value()

        if not inp.exists():
            QMessageBox.information(self, "Training", f"Input path does not exist: {inp}")
            return
        out_dir.mkdir(parents=True, exist_ok=True)

        python = venv_python()
        if self.chk_use_make.isChecked():
            # For parity we stick to direct CLI unless requested
            cmd = ["make", "cgir-train"]
        else:
            cmd = [
                python,
                str(repo_root() / "tools" / "cgir" / "cli_train.py"),
                "--in", str(inp),
                "--out", str(out_dir),
                "--quantize-dp", str(dp),
            ]

        # Clear console, table, chart and run
        self.console.clear()
        self._clear_table()
        self._clear_chart()

        self._last_input = inp
        self._last_out_dir = out_dir
        self._proc.run(cmd, workdir=repo_root())

    def refresh_results(self) -> None:
        if self._last_out_dir is None:
            QMessageBox.information(self, "Refresh", "No output directory yet; run training first.")
            return
        self._load_attrib_files(self._last_out_dir)

    def _on_finished(self, result) -> None:
        exit_code = int(getattr(result, "exit_code", -1))
        self._append_log(f"\n[train finished with exit code {exit_code}]\n")
        self.finished.emit(exit_code)
        # Attempt to load results automatically
        if self._last_out_dir is not None:
            self._load_attrib_files(self._last_out_dir)

    def _on_choose_attrib_file(self, idx: int) -> None:
        if not (0 <= idx < len(self._attrib_files)):
            return
        self._load_attrib_file(self._attrib_files[idx])

    def _on_table_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        r = rows[0].row()
        if not (0 <= r < len(self._events)):
            return
        self._plot_event(self._events[r])

    # -------------------------
    # Internal: Loading results
    # -------------------------
    def _load_attrib_files(self, out_dir: Path) -> None:
        # Gather *_attrib.json files
        files = sorted(out_dir.rglob("*_attrib.json"))
        self._attrib_files = files
        self.combo_files.blockSignals(True)
        self.combo_files.clear()
        for f in files:
            self.combo_files.addItem(f.name, userData=str(f))
        self.combo_files.blockSignals(False)

        if files:
            # Load first by default
            self._load_attrib_file(files[0])
        else:
            self._clear_table()
            self._clear_chart()
            self._append_log("[info] No _attrib.json files found yet\n")

    def _load_attrib_file(self, path: Path) -> None:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Load Attribution Error", f"{path}: {e}")
            return

        events = []
        for ev in data.get("events", []) or []:
            if "error" in ev:
                events.append(AttribEvent(
                    index=int(ev.get("index", -1)),
                    target_ok=(0.0, 0.0, 0.0),
                    alphas=[],
                    residual_norm=0.0,
                    sum_alpha_before_norm=0.0,
                    normalized=False,
                    error=str(ev.get("error")),
                ))
                continue
            try:
                idx = int(ev.get("index", -1))
                tgt = ev.get("target_ok", {})
                target = (float(tgt.get("L", 0.0)), float(tgt.get("a", 0.0)), float(tgt.get("b", 0.0)))
                alphas = [(str(a.get("id")), float(a.get("alpha"))) for a in (ev.get("alphas", []) or [])]
                res = float(ev.get("residual_norm", 0.0))
                sum_a = float(ev.get("sum_alpha_before_norm", 0.0))
                normed = bool(ev.get("normalized", False))
                events.append(AttribEvent(
                    index=idx,
                    target_ok=target,
                    alphas=alphas,
                    residual_norm=res,
                    sum_alpha_before_norm=sum_a,
                    normalized=normed,
                ))
            except Exception as e:
                events.append(AttribEvent(
                    index=int(ev.get("index", -1)),
                    target_ok=(0.0, 0.0, 0.0),
                    alphas=[],
                    residual_norm=0.0,
                    sum_alpha_before_norm=0.0,
                    normalized=False,
                    error=f"parse error: {e}",
                ))

        self._events = events
        self._populate_table(events)
        # Plot first event if available
        if events:
            self.table.selectRow(0)
            self._plot_event(events[0])
        else:
            self._clear_chart()

    # -------------------------
    # Internal: Table/Chart
    # -------------------------
    def _populate_table(self, events: List[AttribEvent]) -> None:
        self.table.setRowCount(len(events))
        for r, ev in enumerate(events):
            def _set(c: int, text: str) -> None:
                item = QTableWidgetItem(text)
                if ev.error:
                    item.setForeground(Qt.red)
                self.table.setItem(r, c, item)

            _set(0, str(ev.index))
            _set(1, f"{ev.residual_norm:.6g}" if not ev.error else "error")
            _set(2, "true" if ev.normalized else "false")
            _set(3, f"{ev.sum_alpha_before_norm:.6g}")

    def _plot_event(self, ev: AttribEvent) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if ev.error:
            ax.text(0.5, 0.5, f"Error: {ev.error}", ha="center", va="center", color="red", transform=ax.transAxes)
        else:
            names = [n for (n, _) in ev.alphas] or ["<none>"]
            vals = [v for (_, v) in ev.alphas] or [0.0]
            x = np.arange(len(names))
            ax.bar(x, vals, color="#4a7c59")
            ax.set_xticks(x, names, rotation=45, ha="right")
            ax.set_ylim(0.0, 1.0)
            ax.set_ylabel("alpha")
            ax.set_title(f"Event {ev.index} — residual={ev.residual_norm:.6g}, normalized={ev.normalized}")
            ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.4)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _clear_table(self) -> None:
        self.table.clearContents()
        self.table.setRowCount(0)

    def _clear_chart(self) -> None:
        self.figure.clear()
        self.canvas.draw_idle()

    def _append_log(self, text: str) -> None:
        self.console.moveCursor(self.console.textCursor().End)
        self.console.insertPlainText(text)
        self.console.moveCursor(self.console.textCursor().End)
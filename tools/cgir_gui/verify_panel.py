# pylint: disable=import-error,no-name-in-module

from __future__ import annotations

from pathlib import Path
from typing import Optional

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
    QDoubleSpinBox,
    QTextEdit,
    QMessageBox,
    QSizePolicy,
    QCheckBox,
)

from .process_controller import ProcessController


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def venv_python() -> str:
    root = repo_root()
    cand = root / ".venv" / "bin" / "python"
    return str(cand) if cand.exists() else "python3"


def default_sim_dir() -> str:
    return str(repo_root() / "build" / "cgir" / "sim")


class VerifyPanel(QWidget):
    """
    Side-by-side artifact verification panel.

    Features:
      - Pick Directory/File A and B
      - Tolerance control (1e-4 .. 1e-12)
      - Run verification via tools/cgir/cli_verify.py
      - Show textual results, highlight failures
      - Optionally stop on first failure (future toggle)

    Emits:
      - finished(int): exit code (0 OK, nonzero failure)
    """

    finished = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._proc = ProcessController(self)
        self._proc.started.connect(lambda s: self._append(f"$ {s}\n"))
        self._proc.output.connect(self._append)
        self._proc.finished.connect(self._on_finished)
        self._proc.error.connect(lambda e: self._append(f"[error] {e}\n"))

    def _build_ui(self) -> None:
        root = QVBoxLayout()

        form = QFormLayout()

        # Paths A and B
        self.edit_a = QLineEdit(default_sim_dir())
        self.btn_a = QPushButton("Browse…")
        self.btn_a.clicked.connect(self._choose_a)
        row_a = QHBoxLayout()
        row_a.addWidget(self.edit_a, stretch=1)
        row_a.addWidget(self.btn_a)

        self.edit_b = QLineEdit(default_sim_dir())
        self.btn_b = QPushButton("Browse…")
        self.btn_b.clicked.connect(self._choose_b)
        row_b = QHBoxLayout()
        row_b.addWidget(self.edit_b, stretch=1)
        row_b.addWidget(self.btn_b)

        # Tolerance
        self.spin_tol = QDoubleSpinBox()
        self.spin_tol.setDecimals(12)
        self.spin_tol.setRange(1e-12, 1e-4)
        self.spin_tol.setSingleStep(1e-12)
        self.spin_tol.setValue(1e-12)

        # Controls
        self.chk_use_make = QCheckBox("Use Makefile target (cgir-verify)")
        self.btn_run = QPushButton("Verify")
        self.btn_run.clicked.connect(self.run_verify)

        row_ctrl = QHBoxLayout()
        row_ctrl.addWidget(self.chk_use_make)
        row_ctrl.addStretch()
        row_ctrl.addWidget(self.btn_run)

        form.addRow("Artifact A:", QWidget())
        form.addRow(row_a)
        form.addRow("Artifact B:", QWidget())
        form.addRow(row_b)
        form.addRow("Tolerance (OKLab):", self.spin_tol)
        form.addRow(row_ctrl)

        root.addLayout(form)

        # Results console
        self.console = QTextEdit(self)
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QTextEdit.NoWrap)
        self.console.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.console, stretch=1)

        self.setLayout(root)

    # Helpers
    def _append(self, text: str) -> None:
        self.console.moveCursor(self.console.textCursor().End)
        self.console.insertPlainText(text)
        self.console.moveCursor(self.console.textCursor().End)

    def _choose_a(self) -> None:
        base = self.edit_a.text().strip() or default_sim_dir()
        p = QFileDialog.getExistingDirectory(self, "Choose Artifact Directory A", base)
        if p:
            self.edit_a.setText(p)

    def _choose_b(self) -> None:
        base = self.edit_b.text().strip() or default_sim_dir()
        p = QFileDialog.getExistingDirectory(self, "Choose Artifact Directory B", base)
        if p:
            self.edit_b.setText(p)

    def run_verify(self) -> None:
        A = self.edit_a.text().strip()
        B = self.edit_b.text().strip()
        tol = float(self.spin_tol.value())

        if not A or not B:
            QMessageBox.information(self, "Verify", "Please choose both A and B artifact paths.")
            return

        python = venv_python()
        if self.chk_use_make.isChecked():
            # Makefile route (shell-invoked). Not recommended inside QProcess on Windows by default,
            # but macOS/Linux-friendly; for maximum portability keep the direct CLI path default.
            cmd = ["make", "cgir-verify", f"A={A}", f"B={B}"]
        else:
            cmd = [
                python,
                str(repo_root() / "tools" / "cgir" / "cli_verify.py"),
                "--a", A,
                "--b", B,
                "--tol", f"{tol:.12g}",
            ]

        self.console.clear()
        self._proc.run(cmd, workdir=repo_root())

    def _on_finished(self, result) -> None:
        # result is ProcessResult
        exit_code = int(getattr(result, "exit_code", -1))
        self._append(f"\n[verify finished with exit code {exit_code}]\n")
        self.finished.emit(exit_code)
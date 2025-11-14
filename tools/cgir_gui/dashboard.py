# pylint: disable=import-error,no-name-in-module
from __future__ import annotations

import os
import json
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFormLayout,
    QLineEdit,
    QMessageBox,
)

from .state import load_workspace, save_workspace, update_last_opened, repo_root


class DashboardWidget(QWidget):
    """
    Status Dashboard for CGIR Desktop GUI.

    Shows:
      - Workspace directories and paths
      - Recent files list (click to open in editor via a callback)
      - Quick buttons to open common artifact directories
      - Auto-refresh (interval-based) to reflect external changes to workspace.json

    Integration contract:
      - Parent window wires `on_open_file(path: Path)` to open a file in an editor tab.
      - Parent may call `refresh()` after pipeline actions to update the dashboard live.
    """

    def __init__(self, parent: Optional[QWidget] = None, *, on_open_file=None) -> None:
        super().__init__(parent)
        self._on_open_file = on_open_file
        self._build_ui()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(5000)  # 5 seconds
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Title
        title = QLabel("<h3>CGIR Workspace Dashboard</h3>", self)
        root.addWidget(title)

        # Workspace summary
        self.form = QFormLayout()
        self.edit_workspace = QLineEdit(str(repo_root()))
        self.edit_workspace.setReadOnly(True)
        self.edit_examples = QLineEdit(str(repo_root() / "examples" / "cgir"))
        self.edit_examples.setReadOnly(True)
        self.edit_build = QLineEdit(str(repo_root() / "build" / "cgir"))
        self.edit_build.setReadOnly(True)

        self.form.addRow("Project Root:", self.edit_workspace)
        self.form.addRow("Examples Folder:", self.edit_examples)
        self.form.addRow("Build Artifacts:", self.edit_build)

        root.addLayout(self.form)

        # Project Stats section
        root.addWidget(QLabel("<b>Project Stats</b>", self))
        self.stats_form = QFormLayout()
        self.lbl_examples_count = QLabel("-", self)
        self.lbl_sim_count = QLabel("-", self)
        self.lbl_last_run = QLabel("-", self)
        self.stats_form.addRow("Examples (.json):", self.lbl_examples_count)
        self.stats_form.addRow("Sim artifacts:", self.lbl_sim_count)
        self.stats_form.addRow("Last run:", self.lbl_last_run)
        root.addLayout(self.stats_form)

        # Quick actions
        qa = QHBoxLayout()
        btn_open_root = QPushButton("Open Project Root")
        btn_open_root.clicked.connect(lambda: self._open_in_finder(Path(self.edit_workspace.text())))
        qa.addWidget(btn_open_root)

        btn_open_examples = QPushButton("Open Examples")
        btn_open_examples.clicked.connect(lambda: self._open_in_finder(Path(self.edit_examples.text())))
        qa.addWidget(btn_open_examples)

        btn_open_build = QPushButton("Open Build Artifacts")
        btn_open_build.clicked.connect(lambda: self._open_in_finder(Path(self.edit_build.text())))
        qa.addWidget(btn_open_build)

        qa.addStretch()
        root.addLayout(qa)

        # Recent files
        root.addWidget(QLabel("<b>Recent Files</b>", self))
        self.list_recents = QListWidget(self)
        self.list_recents.itemActivated.connect(self._open_recent)
        root.addWidget(self.list_recents)

        # Manual refresh
        bar = QHBoxLayout()
        btn_refresh = QPushButton("Refresh Now")
        btn_refresh.clicked.connect(self.refresh)
        bar.addStretch()
        bar.addWidget(btn_refresh)
        root.addLayout(bar)

        # Footnote
        hint = QLabel(
            "<small>Tip: The dashboard auto-refreshes every 5 seconds. "
            "It reflects workspace state written to .cgir/workspace.json.</small>",
            self,
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

    def refresh(self) -> None:
        """
        Reload dashboard from workspace state and compute project stats.
        """
        try:
            st = load_workspace()
            # Paths
            if st.last_opened_dir:
                try:
                    examples_dir = Path(st.last_opened_dir)
                    proj_root = repo_root()
                    if examples_dir.name == "cgir" and examples_dir.parent.name == "examples":
                        self.edit_workspace.setText(str(proj_root))
                    else:
                        self.edit_workspace.setText(str(examples_dir.parent))
                    self.edit_examples.setText(str(examples_dir))
                except Exception:
                    self.edit_examples.setText(st.last_opened_dir)
            if st.params and st.params.out_dir:
                self.edit_build.setText(st.params.out_dir)

            # Populate recents
            self.list_recents.clear()
            for p in st.recent_files:
                self.list_recents.addItem(QListWidgetItem(str(p)))

            # Compute stats
            ex_dir = Path(self.edit_examples.text().strip())
            sim_dir = Path(self.edit_build.text().strip()) / "sim"
            try:
                ex_count = sum(1 for _ in ex_dir.rglob("*.json")) if ex_dir.exists() else 0
            except Exception:
                ex_count = 0
            try:
                sim_count = sum(1 for _ in sim_dir.rglob("*.json")) if sim_dir.exists() else 0
            except Exception:
                sim_count = 0
            self.lbl_examples_count.setText(str(ex_count))
            self.lbl_sim_count.setText(str(sim_count))

            # Last run info
            runs_dir = repo_root() / ".cgir" / "runs"
            last_text = "—"
            if runs_dir.exists():
                try:
                    last = max(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, default=None)
                    if last:
                        with last.open("r", encoding="utf-8") as fh:
                            meta = json.load(fh)
                        task = (meta.get("metadata") or {}).get("task")
                        exit_code = meta.get("exit_code")
                        t = meta.get("finished_at") or meta.get("started_at")
                        if t:
                            timestr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(t)))
                        else:
                            timestr = ""
                        last_text = f"{task or 'run'} exit {exit_code} at {timestr}"
                except Exception:
                    last_text = "n/a"
            self.lbl_last_run.setText(last_text)
        except Exception as e:
            QMessageBox.warning(self, "Dashboard", f"Failed to refresh workspace: {e}")

    # Helpers
    def _open_in_finder(self, path: Path) -> None:
        try:
            if not path.exists():
                QMessageBox.information(self, "Open Path", f"Path does not exist:\n{path}")
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as e:
            QMessageBox.warning(self, "Open Path", f"Failed to open:\n{path}\n\n{e}")

    def _open_recent(self, item: QListWidgetItem) -> None:
        p = Path(item.text())
        if not p.exists():
            QMessageBox.information(self, "Recent File", f"File does not exist:\n{p}")
            return
        if callable(self._on_open_file):
            try:
                self._on_open_file(p)
            except Exception as e:
                QMessageBox.critical(self, "Open Recent", f"Failed to open in editor:\n{p}\n\n{e}")
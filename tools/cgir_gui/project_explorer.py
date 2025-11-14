# pylint: disable=import-error,no-name-in-module

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeView,
    QFileSystemModel,
    QPushButton,
    QFileDialog,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_examples_dir() -> str:
    return str(repo_root() / "examples" / "cgir")


class ProjectExplorer(QWidget):
    """
    Minimal project explorer for CGIR examples.

    - Shows a QFileSystemModel filtered to *.json
    - Button to select a new root directory
    - Public API:
        * selected_path() -> Optional[Path]
        * set_root(path: str) -> None
    """

    def __init__(self, parent: Optional[QWidget] = None, initial: Optional[str] = None) -> None:
        super().__init__(parent)
        self.root_path: str = initial or default_examples_dir()
        self._build_ui()

    def _build_ui(self) -> None:
        # Build file system model
        self.model = QFileSystemModel(self)
        self.model.setNameFilters(["*.json"])
        self.model.setNameFilterDisables(False)
        self.model.setRootPath(self.root_path)

        # Tree view
        self.tree = QTreeView(self)
        self.tree.setAccessibleName("project_explorer_tree")
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.root_path))
        self.tree.setSelectionMode(QTreeView.SingleSelection)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)

        # Controls
        btn_row = QHBoxLayout()
        self.btn_open = QPushButton("Open Folder…")
        self.btn_open.clicked.connect(self._choose_root)
        btn_row.addWidget(self.btn_open)
        btn_row.addStretch()

        # Layout
        layout = QVBoxLayout()
        layout.addLayout(btn_row)
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def selected_path(self) -> Optional[Path]:
        idx = self.tree.currentIndex()
        if not idx.isValid():
            return None
        p = self.model.filePath(idx)
        return Path(p) if p else None

    def set_root(self, path: str) -> None:
        if not path:
            return
        self.root_path = path
        idx = self.model.setRootPath(self.root_path)
        self.tree.setRootIndex(idx)

    def _choose_root(self) -> None:
        p = QFileDialog.getExistingDirectory(self, "Open Workspace", self.root_path)
        if p:
            self.set_root(p)
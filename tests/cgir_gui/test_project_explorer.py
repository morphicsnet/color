# pylint: disable=import-error,no-name-in-module
from __future__ import annotations

import os
import sys
from pathlib import Path

# Headless Qt
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtWidgets import QApplication  # type: ignore

from tools.cgir_gui.project_explorer import ProjectExplorer  # type: ignore


def test_project_explorer_smoke(tmp_path):
    app = QApplication.instance() or QApplication([])

    # Create files: two JSON and one non-JSON
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    c = tmp_path / "notes.txt"
    a.write_text("{}", encoding="utf-8")
    b.write_text("{}", encoding="utf-8")
    c.write_text("not json", encoding="utf-8")

    # Instantiate and set root to temp directory
    w = ProjectExplorer(None)
    try:
        # API: set_root should update view without exceptions
        w.set_root(str(tmp_path))

        # Accessibility name set
        assert w.tree.accessibleName() == "project_explorer_tree"

        # QFileSystemModel should be filtering to JSONs
        assert w.model.nameFilters() == ["*.json"]
        assert not w.model.nameFilterDisables()

        # Programmatically select a JSON file and ensure selected_path() returns a Path
        idx = w.model.index(str(a))
        assert idx.isValid()
        w.tree.setCurrentIndex(idx)
        sel = w.selected_path()
        assert sel is not None and sel.name == "a.json"
    finally:
        w.deleteLater()
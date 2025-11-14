#!/usr/bin/env python3
# pylint: disable=import-error,no-name-in-module
"""
CGIR Desktop GUI - Application Entrypoint

Bootstraps a PySide6 QApplication and launches the MainWindow. This GUI integrates
the CGIR toolchain (validate, simulate, visualize, verify, train) into a unified
workspace.

Run:
  python -m tools.cgir_gui.app
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication
except Exception as e:
    print("ERROR: PySide6 is required. Install GUI deps via:", file=sys.stderr)
    print("  pip install -r tools/cgir_gui/requirements.txt", file=sys.stderr)
    raise

# Attempt to import the main window. Provide a fallback placeholder if not yet created.
try:
    from .main_window import MainWindow  # type: ignore
except Exception:
    from PySide6.QtWidgets import QMainWindow

    class MainWindow(QMainWindow):  # placeholder until main_window.py exists
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("CGIR Desktop (Scaffold)")
            self.resize(1100, 700)


def _load_qss_file(path: Path) -> str:
    """Safely load a QSS file; return empty string on error."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""

def _apply_env_theme(app: "QApplication") -> None:
    """
    Apply a QSS theme based on CGIR_THEME env var ("dark" or "light").
    If unset or file missing, does nothing. Non-fatal on errors.
    """
    try:
        theme = (os.getenv("CGIR_THEME") or "").strip().lower()
        if theme not in ("dark", "light"):
            return
        resources_dir = Path(__file__).resolve().parent / "resources"
        qss_path = resources_dir / f"{theme}.qss"
        qss = _load_qss_file(qss_path)
        if qss:
            app.setStyleSheet(qss)
    except Exception:
        # Non-fatal if theme application fails
        pass

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    # Ensure we run from repo root when launched via -m
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    app = QApplication(argv)
    _apply_env_theme(app)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
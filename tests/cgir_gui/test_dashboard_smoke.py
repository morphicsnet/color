# pylint: disable=import-error,no-name-in-module
from __future__ import annotations

import json
import os
from pathlib import Path

# Headless Qt
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # type: ignore

import tools.cgir_gui.dashboard as dashboard_module  # type: ignore
from tools.cgir_gui.dashboard import DashboardWidget  # type: ignore


def test_dashboard_stats(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])

    # Create a fake repo structure under tmp_path
    repo_dir = tmp_path / "repo"
    examples_dir = repo_dir / "examples" / "cgir"
    sim_dir = repo_dir / "build" / "cgir" / "sim"
    runs_dir = repo_dir / ".cgir" / "runs"
    examples_dir.mkdir(parents=True, exist_ok=True)
    sim_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Two example CGIR JSONs
    (examples_dir / "a.json").write_text('{"cgir_version":"0.1.0"}\n', encoding="utf-8")
    (examples_dir / "b.json").write_text('{"cgir_version":"0.1.0"}\n', encoding="utf-8")

    # One simulated artifact
    (sim_dir / "a.json").write_text('{"ok":true}\n', encoding="utf-8")

    # Last run metadata
    last_run = runs_dir / "20250101-010101.json"
    last_run.write_text(
        json.dumps(
            {
                "metadata": {"task": "simulate"},
                "exit_code": 0,
                "started_at": 1735689600.0,  # 2025-01-01 00:00:00 UTC
                "finished_at": 1735689660.0,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Provide a minimal workspace stub to dashboard.load_workspace()
    class _Params:
        def __init__(self, out_dir: str) -> None:
            self.out_dir = out_dir

    class _WS:
        def __init__(self, last_opened_dir: str, out_dir: str) -> None:
            self.last_opened_dir = last_opened_dir
            self.params = _Params(out_dir)
            self.recent_files = []

    ws = _WS(str(examples_dir), str(repo_dir / "build" / "cgir"))

    monkeypatch.setattr(dashboard_module, "load_workspace", lambda: ws)
    monkeypatch.setattr(dashboard_module, "repo_root", lambda: repo_dir)

    w = DashboardWidget(on_open_file=None)
    try:
        # Force refresh using our stubbed workspace and repo_root
        w.refresh()

        # Validate computed stats
        assert w.lbl_examples_count.text().isdigit()
        assert int(w.lbl_examples_count.text()) == 2

        assert w.lbl_sim_count.text().isdigit()
        assert int(w.lbl_sim_count.text()) == 1

        # Last run should reflect exit code 0
        assert "exit 0" in w.lbl_last_run.text()
    finally:
        w.deleteLater()
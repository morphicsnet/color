# Basic GUI smoke tests for CGIR Desktop
# Runs headless with QT_QPA_PLATFORM=offscreen and verifies that the main
# window can be constructed and that ProcessController executes a trivial command.

from __future__ import annotations

import os
import sys
from pathlib import Path

# Run headless
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtWidgets import QApplication  # type: ignore
from PySide6.QtCore import QEventLoop, QTimer  # type: ignore

from tools.cgir_gui.main_window import MainWindow  # type: ignore
from tools.cgir_gui.process_controller import ProcessController  # type: ignore


def test_app_launch():
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    try:
        # Window title should contain CGIR
        assert "CGIR" in win.windowTitle()
    finally:
        win.close()
        # keep the QApplication alive for the next test


def test_process_controller_runs_python_echo(tmp_path):
    app = QApplication.instance() or QApplication([])

    pc = ProcessController()
    done: dict[str, object] = {"result": None}

    def _on_finished(res):
        done["result"] = res

    loop = QEventLoop()
    pc.finished.connect(lambda res: (_on_finished(res), loop.quit()))

    py = sys.executable
    pc.run([py, "-c", "print('ok')"], workdir=REPO_ROOT)

    # Safety timeout to avoid hanging the test in case of failures
    timer = QTimer()
    timer.setSingleShot(True)
    timer.setInterval(10000)  # 10s
    timer.timeout.connect(loop.quit)
    timer.start()

    loop.exec()

    assert done["result"] is not None, "Process did not finish"
    res = done["result"]
    exit_code = int(getattr(res, "exit_code", -1))
    stdout = str(getattr(res, "stdout", ""))
    assert exit_code == 0
    assert "ok" in stdout
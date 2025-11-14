# pylint: disable=import-error,no-name-in-module

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class ProcessResult:
    exit_code: int
    stdout: str
    log_path: Optional[Path] = None
    run_meta: Optional[Dict[str, Any]] = None


class ProcessController(QObject):
    """
    QProcess wrapper with:
      - Signals for started/output/finished/error/timeout
      - Optional timeout with hard-kill grace period
      - Structured reproducibility capture to .cgir/runs/*.json
      - Streaming log file to .cgir/logs/*.log
    """

    started = Signal(str)
    output = Signal(str)
    finished = Signal(ProcessResult)
    error = Signal(str)
    timeout = Signal()

    # Optional sink (e.g., QTextEdit) set by owner; not strictly required
    log_sink: Optional[Any] = None

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._proc: Optional[QProcess] = None
        self._buffer: list[str] = []
        self._workdir: Optional[Path] = None
        self._on_finish: Optional[Callable[[int], None]] = None

        self._timeout_timer: Optional[QTimer] = None
        self._kill_timer: Optional[QTimer] = None

        self._log_path: Optional[Path] = None
        self._log_fh: Optional[Any] = None
        self._run_json_path: Optional[Path] = None
        self._run_meta: Dict[str, Any] = {}

    def run(
        self,
        cmd: list[str],
        workdir: Optional[Path] = None,
        on_finish: Optional[Callable[[int], None]] = None,
        *,
        env: Optional[Dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Start a command. If a process is already running, emit error and ignore.
        """
        if self._proc is not None:
            self.error.emit("Process already running")
            return

        self._workdir = workdir
        self._on_finish = on_finish
        self._buffer = []
        self._run_meta = {
            "cmd": cmd,
            "workdir": str(workdir) if workdir else None,
            "started_at": time.time(),
            "env_overrides": dict(env) if env else None,
            "metadata": dict(metadata) if metadata else None,
        }

        # Prepare run/log paths
        runs_dir = repo_root() / ".cgir" / "runs"
        logs_dir = repo_root() / ".cgir" / "logs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        self._log_path = logs_dir / f"{ts}.log"
        self._run_json_path = runs_dir / f"{ts}.json"

        # Open log file
        try:
            self._log_fh = self._log_path.open("w", encoding="utf-8")
            self._log_fh.write(f"# started_at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._log_fh.write(f"# workdir: {self._workdir}\n")
            self._log_fh.write(f"$ {' '.join(cmd)}\n")
            self._log_fh.flush()
        except Exception as e:
            self._safe_emit_error(f"Failed to open log file: {e}")
            self._cleanup()
            return

        proc = QProcess(self)
        self._proc = proc

        if workdir:
            proc.setWorkingDirectory(str(workdir))

        # Environment
        try:
            env_obj = QProcessEnvironment.systemEnvironment()
            if env:
                for k, v in env.items():
                    env_obj.insert(str(k), str(v))
            proc.setProcessEnvironment(env_obj)
        except Exception:
            # Non-fatal: fall back to system env
            pass

        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(self._read_output)
        proc.readyReadStandardError.connect(self._read_output)
        proc.errorOccurred.connect(self._on_error)
        proc.finished.connect(self._on_finished)

        # Timeout handling
        if timeout_ms and timeout_ms > 0:
            self._timeout_timer = QTimer(self)
            self._timeout_timer.setSingleShot(True)
            self._timeout_timer.setInterval(int(timeout_ms))
            self._timeout_timer.timeout.connect(self._on_timeout)
            self._timeout_timer.start()

        cmd_str = " ".join(cmd)
        self.started.emit(cmd_str)
        try:
            proc.start(cmd[0], cmd[1:])
        except Exception as e:
            self._safe_log(f"[spawn failed] {e}\n")
            self._cleanup()
            self._safe_emit_error(f"Spawn failed: {e}")

    def terminate(self) -> None:
        """
        Politely request termination. If QProcess is None, ignore.
        """
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            # Hard-kill after grace if still running
            self._kill_timer = QTimer(self)
            self._kill_timer.setSingleShot(True)
            self._kill_timer.setInterval(2000)
            self._kill_timer.timeout.connect(self._kill_now)
            self._kill_timer.start()
        except Exception as e:
            self._safe_emit_error(f"Terminate failed: {e}")

    # Internals
    def _read_output(self) -> None:
        if self._proc is None:
            return
        chunk = self._proc.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        if not chunk:
            return
        self._buffer.append(chunk)
        self.output.emit(chunk)
        self._safe_log(chunk)

    def _on_error(self, _qproc_err) -> None:
        self._safe_log("[error] QProcess reported an error\n")
        self.error.emit("Process error signaled by QProcess")

    def _on_timeout(self) -> None:
        self._safe_log("[timeout] Process exceeded timeout; attempting terminate\n")
        self.timeout.emit()
        self.terminate()

    def _kill_now(self) -> None:
        if self._proc is None:
            return
        try:
            self._safe_log("[kill] Force killing process\n")
            self._proc.kill()
        except Exception:
            pass

    def _on_finished(self, code: int, _status) -> None:
        text = "".join(self._buffer)
        # Persist run meta
        try:
            payload = dict(self._run_meta)
            payload.update(
                {
                    "finished_at": time.time(),
                    "exit_code": int(code),
                    "log_path": str(self._log_path) if self._log_path else None,
                }
            )
            if self._run_json_path:
                with self._run_json_path.open("w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=2, ensure_ascii=False)
                    fh.write("\n")
        except Exception:
            # Non-fatal
            pass

        self.finished.emit(
            ProcessResult(
                exit_code=code,
                stdout=text,
                log_path=self._log_path,
                run_meta=self._run_meta,
            )
        )
        if self._on_finish:
            try:
                self._on_finish(code)
            except Exception:
                # Swallow UI callback exceptions; they belong to the caller
                pass
        self._cleanup()

    def _safe_log(self, text: str) -> None:
        try:
            if self._log_fh:
                self._log_fh.write(text)
                self._log_fh.flush()
        except Exception:
            pass

    def _safe_emit_error(self, msg: str) -> None:
        try:
            self.error.emit(msg)
        except Exception:
            pass

    def _cleanup(self) -> None:
        try:
            if self._timeout_timer:
                self._timeout_timer.stop()
            if self._kill_timer:
                self._kill_timer.stop()
        except Exception:
            pass
        try:
            if self._log_fh:
                self._log_fh.flush()
                self._log_fh.close()
        except Exception:
            pass
        self._proc = None
        self._buffer = []
        self._workdir = None
        self._on_finish = None
        self._timeout_timer = None
        self._kill_timer = None
        self._log_fh = None
        self._log_path = None
        self._run_json_path = None
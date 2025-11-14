# pylint: disable=import-error,no-name-in-module
from __future__ import annotations

import threading
from pathlib import Path
from typing import Iterable, Optional, Set

from PySide6.QtCore import QObject, QTimer, Signal
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    _HAS_WATCHDOG = True
except Exception:
    # Provide a no-op fallback if watchdog is unavailable
    Observer = object  # type: ignore
    FileSystemEventHandler = object  # type: ignore
    FileSystemEvent = object  # type: ignore
    _HAS_WATCHDOG = False


class _Handler(FileSystemEventHandler):  # type: ignore[misc]
    """
    Watchdog event handler that notifies a callback with the changed path.
    """

    def __init__(self, on_change) -> None:
        super().__init__()
        self._on_change = on_change

    # Watchdog will call into this thread when FS events occur
    def on_any_event(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        try:
            src = getattr(event, "src_path", None)
            if src:
                self._on_change(str(src))
        except Exception:
            # Best-effort; swallow errors inside FS callbacks
            pass


class FSWatcher(QObject):
    """
    Qt-friendly filesystem watcher using watchdog.

    Features:
    - Start/stop lifecycle
    - Debounced 'changed' signal (aggregates bursts of FS events)
    - Can watch multiple paths/directories recursively

    Signals:
    - changed(str path): emitted after debounce when any file under watched paths changes
    """

    changed = Signal(str)

    def __init__(self, parent: Optional[QObject] = None, *, debounce_ms: int = 250) -> None:
        super().__init__(parent)
        self._observer: Optional[Observer] = None  # type: ignore[assignment]
        self._handler: Optional[_Handler] = None
        self._paths: Set[Path] = set()
        self._last_path: Optional[str] = None

        # Debounce timer to coalesce bursts of changes
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(int(debounce_ms))
        self._debounce.timeout.connect(self._emit_debounced)

        self._lock = threading.Lock()

    def is_running(self) -> bool:
        return self._observer is not None

    def add_path(self, path: str | Path) -> None:
        p = Path(path)
        self._paths.add(p)

    def clear_paths(self) -> None:
        self._paths.clear()

    def start(self) -> bool:
        """
        Start the watchdog observer. Returns True if started, False if watchdog unavailable
        or already running.
        """
        if not _HAS_WATCHDOG:
            return False
        if self._observer is not None:
            return False

        obs = Observer()
        self._observer = obs
        self._handler = _Handler(self._on_fs_event)

        for p in self._paths:
            try:
                base = p if p.is_dir() else p.parent
                obs.schedule(self._handler, str(base), recursive=True)
            except Exception:
                # Ignore invalid paths; continue scheduling others
                continue

        try:
            obs.start()
            return True
        except Exception:
            self.stop()
            return False

    def stop(self) -> None:
        if self._observer is None:
            return
        try:
            self._observer.stop()
            self._observer.join(timeout=2.0)
        except Exception:
            pass
        finally:
            self._observer = None
            self._handler = None

    def watch(self, paths: Iterable[str | Path]) -> bool:
        """
        Convenience: set paths and start.
        """
        self.clear_paths()
        for p in paths:
            self.add_path(p)
        return self.start()

    # Internal

    def _on_fs_event(self, src_path: str) -> None:
        # Called from watchdog thread; make thread-safe and debounce
        try:
            with self._lock:
                self._last_path = src_path
                # Restart debounce timer in the GUI thread
                # Using singleShot pattern to coalesce frequent events
                self._debounce.start()
        except Exception:
            pass

    def _emit_debounced(self) -> None:
        try:
            with self._lock:
                last = self._last_path
                self._last_path = None
            if last:
                self.changed.emit(last)
        except Exception:
            pass
# pylint: disable=import-error,no-name-in-module

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
)
from .state import load_workspace, save_workspace, update_params

try:
    from jsonschema import Draft202012Validator
    _HAS_JSONSCHEMA = True
except Exception:
    Draft202012Validator = None  # type: ignore
    _HAS_JSONSCHEMA = False


def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def _load_json(text: str) -> Any:
    return json.loads(text)


def _load_schema(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class JsonEditorWidget(QWidget):
    """
    JSON Editor with optional real-time schema validation.

    UI:
      - top bar: schema path (editable) + "Browse..." + "Validate now"
      - editor: QPlainTextEdit
      - diagnostics list: shows validation error messages

    Signals:
      - diagnosticsUpdated(list[str]): validation messages
      - textParsed(obj: Any): emitted when text parses as JSON successfully
    """

    diagnosticsUpdated = Signal(list)
    textParsed = Signal(object)

    def __init__(self, parent: Optional[QObject] = None, *, schema_path: Optional[str] = None) -> None:
        super().__init__(parent)
        self._schema_path: Optional[Path] = Path(schema_path) if schema_path else None
        self._schema: Optional[Any] = None
        self._validator: Optional[Draft202012Validator] = None  # type: ignore
        self._build_ui()
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(400)
        self._debounce.timeout.connect(self._validate_now)
        self._current_path: Optional[Path] = None

        if self._schema_path:
            self._try_load_schema(self._schema_path)

    def _build_ui(self) -> None:
        layout = QVBoxLayout()

        # Schema chooser row
        hl = QHBoxLayout()
        self.schema_edit = QLineEdit(self._schema_path.as_posix() if self._schema_path else "")
        self.btn_schema_browse = QPushButton("Browse…")
        self.btn_schema_browse.clicked.connect(self._on_browse_schema)
        self.btn_validate = QPushButton("Validate now")
        self.btn_validate.clicked.connect(self._validate_now)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #666;")

        hl.addWidget(QLabel("Schema:"))
        hl.addWidget(self.schema_edit, stretch=1)
        hl.addWidget(self.btn_schema_browse)
        hl.addWidget(self.btn_validate)

        layout.addLayout(hl)

        hl2 = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save_as = QPushButton("Save As…")
        self.btn_save_as.clicked.connect(self._on_save_as)
        self.btn_format = QPushButton("Format")
        self.btn_format.clicked.connect(self._on_format)
        self.btn_set_default_schema = QPushButton("Set as Default Schema")
        self.btn_set_default_schema.clicked.connect(self._on_set_default_schema)
        for w in (self.btn_save, self.btn_save_as, self.btn_format, self.btn_set_default_schema):
            hl2.addWidget(w)
        hl2.addStretch()

        layout.addLayout(hl2)
        layout.addWidget(self.lbl_status)

        # Editor
        self.editor = QPlainTextEdit(self)
        self.editor.setPlaceholderText("{\n  \"cgir_version\": \"0.1.0\",\n  \"droplet\": { ... }\n}")
        self.editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.editor, stretch=1)

        # Diagnostics list
        self.diag_list = QListWidget(self)
        layout.addWidget(self.diag_list, stretch=0)

        self.setLayout(layout)
        # Accessibility names
        self.editor.setAccessibleName("json_editor")
        self.diag_list.setAccessibleName("diagnostics")

    # Public API
    def set_schema_path(self, path: Optional[str]) -> None:
        self._schema_path = Path(path) if path else None
        self.schema_edit.setText(self._schema_path.as_posix() if self._schema_path else "")
        if self._schema_path:
            self._try_load_schema(self._schema_path)

    def load_file(self, path: Path) -> None:
        try:
            text = _read_text(path)
            self.editor.setPlainText(text)
            self._current_path = Path(path)
            self.lbl_status.setText(f"Loaded: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Open File Error", f"{path}: {e}")

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text)

    def text(self) -> str:
        return self.editor.toPlainText()

    def parsed(self) -> Optional[Any]:
        try:
            return _load_json(self.text())
        except Exception:
            return None

    # Internal
    def _on_browse_schema(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Choose Schema", self.schema_edit.text().strip() or ".", "JSON (*.json)")
        if p:
            self.set_schema_path(p)

    def _try_load_schema(self, path: Path) -> None:
        try:
            self._schema = _load_schema(path)
            if _HAS_JSONSCHEMA and self._schema is not None:
                self._validator = Draft202012Validator(self._schema)  # type: ignore
            self.lbl_status.setText(f"Loaded schema: {path}")
        except Exception as e:
            self._schema = None
            self._validator = None
            self.lbl_status.setText(f"Schema load error: {e}")

    def _on_text_changed(self) -> None:
        # debounce validation to avoid on-every-keystroke heavy work
        self._debounce.start()

    def _validate_now(self) -> None:
        text = self.text()
        diags: List[str] = []

        # Clear diagnostics view
        self.diag_list.clear()

        # Step 1: parse JSON
        parsed_obj: Optional[Any] = None
        try:
            parsed_obj = _load_json(text)
            self.textParsed.emit(parsed_obj)
        except Exception as e:
            msg = f"JSON parse error: {e}"
            diags.append(msg)
            self.diag_list.addItem(QListWidgetItem(msg))
            self.lbl_status.setText("Invalid JSON")
            self._decorate_editor_valid(False)
            self.diagnosticsUpdated.emit(diags)
            return

        # Step 2: schema validation
        if self._validator is not None and parsed_obj is not None:
            try:
                errors = list(self._validator.iter_errors(parsed_obj))  # type: ignore
                if errors:
                    for err in errors[:50]:
                        loc = "$." + ".".join(str(p) for p in err.path)
                        msg = f"{loc}: {err.message}"
                        diags.append(msg)
                        self.diag_list.addItem(QListWidgetItem(msg))
                    self.lbl_status.setText(f"Schema invalid: {len(errors)} issue(s)")
                    self._decorate_editor_valid(False)
                else:
                    self.lbl_status.setText("Valid JSON (schema OK)")
                    self._decorate_editor_valid(True)
            except Exception as e:
                msg = f"Schema validation error: {e}"
                diags.append(msg)
                self.diag_list.addItem(QListWidgetItem(msg))
                self.lbl_status.setText("Schema validation failed")
                self._decorate_editor_valid(False)
        else:
            # No schema loaded; only JSON checked
            self.lbl_status.setText("Valid JSON (no schema)")

        self.diagnosticsUpdated.emit(diags)

    def _decorate_editor_valid(self, ok: bool) -> None:
        if ok:
            self.editor.setStyleSheet("QPlainTextEdit { background: #f8fff8; }")
        else:
            self.editor.setStyleSheet("QPlainTextEdit { background: #fff8f8; }")

    # -------------------------
    # File ops and utilities
    # -------------------------
    def _prompt_save_as(self) -> Optional[str]:
        p, _ = QFileDialog.getSaveFileName(self, "Save As", "untitled.json", "JSON (*.json)")
        return p or None

    def _on_save(self) -> None:
        p = self._current_path.as_posix() if self._current_path else self._prompt_save_as()
        if not p:
            return
        try:
            parsed = _load_json(self.text())
        except Exception as e:
            QMessageBox.information(self, "Save", f"Cannot save: invalid JSON: {e}")
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
                f.write("\n")
            self._current_path = Path(p)
            self.lbl_status.setText(f"Saved: {p}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"{p}: {e}")

    def _on_save_as(self) -> None:
        p = self._prompt_save_as()
        if p:
            self._current_path = Path(p)
            self._on_save()

    def _on_format(self) -> None:
        try:
            parsed = _load_json(self.text())
            pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
            self.editor.setPlainText(pretty)
            self.lbl_status.setText("Formatted JSON")
        except Exception as e:
            QMessageBox.information(self, "Format", f"Cannot format: invalid JSON: {e}")

    def _on_set_default_schema(self) -> None:
        try:
            ws = load_workspace()
            ws = update_params(ws, schema=self.schema_edit.text().strip())
            save_workspace(ws)
            self.lbl_status.setText("Default schema updated")
        except Exception as e:
            QMessageBox.information(self, "Schema", f"Failed to update default schema: {e}")
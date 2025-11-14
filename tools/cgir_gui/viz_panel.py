# pylint: disable=import-error,no-name-in-module

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
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
    QCheckBox,
    QMessageBox,
    QSizePolicy,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Reuse the same droplet geometry used by the CLI for perfect alignment
try:
    from cgir.core.droplet import cmax_ok_v1
except Exception as e:
    # Provide a minimal fallback so the panel still loads (with a simple envelope)
    def cmax_ok_v1(L: float, h: float) -> float:  # type: ignore
        base = 0.35 * (1.0 - abs(2.0 * L - 1.0)) + 0.05
        ripple = 0.03 * math.sin(3.0 * h)
        return max(0.0, base + ripple)


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _extract_ok_state(node: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
    """
    Return OKLab (L,a,b) if present, else None.
    """
    if not isinstance(node, dict):
        return None
    s = node.get("ok_state")
    if isinstance(s, dict):
        try:
            return float(s["L"]), float(s["a"]), float(s["b"])
        except Exception:
            return None
    return None


def _collect_points(instance: Dict[str, Any]) -> Dict[str, List[Tuple[float, float, float]]]:
    pts: Dict[str, List[Tuple[float, float, float]]] = {"neurons": [], "mix_raw": [], "after_proj": []}
    # Neurons
    for n in instance.get("neurons", []) or []:
        st = n.get("state", {})
        ok = _extract_ok_state(st)
        if ok is not None:
            pts["neurons"].append(ok)
    # Events
    for ev in instance.get("events", []) or []:
        raw = _extract_ok_state(ev.get("mix_raw_ok", {}))
        if raw is not None:
            pts["mix_raw"].append(raw)
        ap = _extract_ok_state(ev.get("after_projection_ok", {}))
        if ap is not None:
            pts["after_proj"].append(ap)
    return pts


class VizPanel(QWidget):
    """
    Live OKLab droplet slice visualization with adjustable L slice and overlays.

    Controls:
      - File picker (CGIR JSON)
      - L slice (0..1)
      - Overlay toggles: neurons, mix_raw_ok, after_projection_ok
      - Render + Export buttons

    Emits:
      - rendered(): when a plot finishes rendering
    """

    rendered = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._path: Optional[Path] = None
        self._last_image_path: Optional[Path] = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout()

        # Controls
        form = QFormLayout()
        self.edit_path = QLineEdit("")
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.clicked.connect(self._choose_file)

        hl = QHBoxLayout()
        hl.addWidget(self.edit_path, stretch=1)
        hl.addWidget(self.btn_browse)

        self.spin_L = QDoubleSpinBox()
        self.spin_L.setDecimals(3)
        self.spin_L.setRange(0.0, 1.0)
        self.spin_L.setSingleStep(0.01)
        self.spin_L.setValue(0.65)

        self.chk_neurons = QCheckBox("Show neurons")
        self.chk_neurons.setChecked(True)
        self.chk_mix = QCheckBox("Show mix_raw_ok")
        self.chk_mix.setChecked(True)
        self.chk_after = QCheckBox("Show after_projection_ok")
        self.chk_after.setChecked(True)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("L slice:"))
        row2.addWidget(self.spin_L)
        row2.addStretch()
        row2.addWidget(self.chk_neurons)
        row2.addWidget(self.chk_mix)
        row2.addWidget(self.chk_after)

        self.btn_render = QPushButton("Render")
        self.btn_render.clicked.connect(self.render_plot)
        self.btn_export = QPushButton("Export PNG…")
        self.btn_export.clicked.connect(self.export_png)

        row3 = QHBoxLayout()
        row3.addStretch()
        row3.addWidget(self.btn_render)
        row3.addWidget(self.btn_export)

        form.addRow("CGIR File:", QWidget())
        form.addRow(hl)
        form.addRow(row2)
        form.addRow(row3)

        root.addLayout(form)

        # Matplotlib canvas
        self.figure = Figure(figsize=(6.5, 6.5), dpi=160)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.canvas, stretch=1)

        self.setLayout(root)

    # UI Actions
    def _choose_file(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Choose CGIR JSON", ".", "JSON (*.json)")
        if p:
            self.edit_path.setText(p)
            self._path = Path(p)

    def render_plot(self) -> None:
        try:
            path_text = self.edit_path.text().strip()
            if not path_text:
                raise ValueError("Select a CGIR JSON file first.")
            path = Path(path_text)
            if not path.exists():
                raise FileNotFoundError(path_text)

            inst = _read_json(path)
            pts = _collect_points(inst)

            L = float(self.spin_L.value())
            self._plot_slice(L, pts)
            self.rendered.emit()
        except Exception as e:
            QMessageBox.critical(self, "Render Error", str(e))

    def export_png(self) -> None:
        try:
            out_path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "viz.png", "PNG (*.png)")
            if not out_path:
                return
            self.figure.savefig(out_path, format="png", dpi=160)
            self._last_image_path = Path(out_path)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    # Plotting
    def _plot_slice(self, L: float, pts: Dict[str, List[Tuple[float, float, float]]]) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Boundary
        n = 720
        hs = np.linspace(-math.pi, math.pi, num=n, endpoint=False)
        Smax = np.array([cmax_ok_v1(L, float(h)) for h in hs], dtype=float)
        a_bnd = Smax * np.cos(hs)
        b_bnd = Smax * np.sin(hs)
        ax.fill(a_bnd, b_bnd, facecolor="#dde8ff", edgecolor="#6688cc", linewidth=1.0, alpha=0.6, label="Droplet slice")

        # Overlays
        tolL = 1e-3

        def _scatter(points: List[Tuple[float, float, float]], color: str, label: str) -> None:
            if not points:
                return
            arr = np.array(points, dtype=float)  # (k,3)
            # Prefer slice points (abs(L-L_slice) small)
            sel = np.where(np.abs(arr[:, 0] - L) <= tolL)[0]
            other = np.where(np.abs(arr[:, 0] - L) > tolL)[0]
            if sel.size > 0:
                ax.scatter(arr[sel, 1], arr[sel, 2], c=color, s=30, marker="o", edgecolors="k", linewidths=0.5, alpha=0.9, label=label)
            if other.size > 0:
                # Subsample 'other' points for performance on large datasets
                max_other = 2000
                if other.size > max_other:
                    try:
                        rng = np.random.default_rng(123)
                        sel_idx = rng.choice(other, size=max_other, replace=False)
                        other_sel = arr[sel_idx]
                    except Exception:
                        other_sel = arr[other[:max_other]]
                else:
                    other_sel = arr[other]
                ax.scatter(other_sel[:, 1], other_sel[:, 2], c=color, s=12, marker=".", alpha=0.25)

        if self.chk_neurons.isChecked():
            _scatter(pts.get("neurons", []), "#555555", "neurons")
        if self.chk_mix.isChecked():
            _scatter(pts.get("mix_raw", []), "#cc3333", "mix_raw_ok")
        if self.chk_after.isChecked():
            _scatter(pts.get("after_proj", []), "#33aa55", "after_projection_ok")

        # Finish
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("a")
        ax.set_ylabel("b")
        ax.set_title(f"OKLab droplet slice at L={L:.3f}")
        ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.4)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            uniq = {}
            for h, lab in zip(handles, labels):
                uniq[lab] = h
            ax.legend(list(uniq.values()), list(uniq.keys()), loc="best", framealpha=0.85)

        self.canvas.draw_idle()
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import time


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def workspace_dir(root: Optional[Path] = None) -> Path:
    root = root or repo_root()
    return root / ".cgir"


def workspace_file(root: Optional[Path] = None) -> Path:
    return workspace_dir(root) / "workspace.json"


@dataclass
class PanelLayout:
    docks: Dict[str, Any] = field(default_factory=dict)  # reserved for future detailed geometry/state


@dataclass
class Parameters:
    schema: str = str(repo_root() / "docs" / "ir" / "cgir-schema.json")
    dp: int = 12
    out_dir: str = str(repo_root() / "build" / "cgir")


@dataclass
class WorkspaceState:
    version: str = "0.1.0"
    last_opened_dir: str = str(repo_root() / "examples" / "cgir")
    last_opened_file: Optional[str] = None
    recent_files: List[str] = field(default_factory=list)
    params: Parameters = field(default_factory=Parameters)
    panel_layout: PanelLayout = field(default_factory=PanelLayout)
    updated_at: float = field(default_factory=lambda: time.time())


def _coerce_parameters(obj: Dict[str, Any]) -> Parameters:
    return Parameters(
        schema=str(obj.get("schema", Parameters.schema)),
        dp=int(obj.get("dp", Parameters.dp)),
        out_dir=str(obj.get("out_dir", Parameters.out_dir)),
    )


def _coerce_layout(obj: Dict[str, Any]) -> PanelLayout:
    return PanelLayout(
        docks=dict(obj.get("docks", {})),
    )


def _coerce_workspace(obj: Dict[str, Any]) -> WorkspaceState:
    params_obj = obj.get("params", {})
    layout_obj = obj.get("panel_layout", {})
    return WorkspaceState(
        version=str(obj.get("version", "0.1.0")),
        last_opened_dir=str(obj.get("last_opened_dir", str(repo_root() / "examples" / "cgir"))),
        last_opened_file=obj.get("last_opened_file"),
        recent_files=[str(p) for p in obj.get("recent_files", [])],
        params=_coerce_parameters(params_obj if isinstance(params_obj, dict) else {}),
        panel_layout=_coerce_layout(layout_obj if isinstance(layout_obj, dict) else {}),
        updated_at=float(obj.get("updated_at", time.time())),
    )


def load_workspace(root: Optional[Path] = None) -> WorkspaceState:
    """
    Load workspace.json from .cgir; returns defaults if not present or parse fails.
    """
    p = workspace_file(root)
    try:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return _coerce_workspace(data if isinstance(data, dict) else {})
    except Exception:
        pass
    return WorkspaceState()


def save_workspace(state: WorkspaceState, root: Optional[Path] = None) -> None:
    """
    Save workspace.json with pretty JSON in .cgir.
    """
    wd = workspace_dir(root)
    wd.mkdir(parents=True, exist_ok=True)
    p = workspace_file(root)
    try:
        payload = asdict(state)
        # Flatten dataclasses
        payload["params"] = asdict(state.params)
        payload["panel_layout"] = asdict(state.panel_layout)
        payload["updated_at"] = time.time()
        with p.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except Exception:
        # Best-effort persistence; swallow exceptions to avoid UI crashes
        pass


def update_last_opened(state: WorkspaceState, *, directory: Optional[str] = None, file: Optional[str] = None) -> WorkspaceState:
    if directory:
        state.last_opened_dir = directory
    if file:
        state.last_opened_file = file
        # Update recents
        try:
            if file in state.recent_files:
                state.recent_files.remove(file)
            state.recent_files.insert(0, file)
            # Keep most recent 20
            state.recent_files = state.recent_files[:20]
        except Exception:
            pass
    state.updated_at = time.time()
    return state


def update_params(state: WorkspaceState, *, schema: Optional[str] = None, dp: Optional[int] = None, out_dir: Optional[str] = None) -> WorkspaceState:
    if schema is not None:
        state.params.schema = schema
    if dp is not None:
        state.params.dp = int(dp)
    if out_dir is not None:
        state.params.out_dir = out_dir
    state.updated_at = time.time()
    return state


def update_panel_layout(state: WorkspaceState, *, docks: Optional[Dict[str, Any]] = None) -> WorkspaceState:
    if docks is not None:
        state.panel_layout.docks = docks
    state.updated_at = time.time()
    return state
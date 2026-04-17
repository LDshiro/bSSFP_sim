"""JSON persistence for Chapter 7 GUI session presets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bssfpviz.gui.session_state import SessionState

SESSION_JSON_VERSION = 1


def save_session_json(path: Path, session: SessionState) -> None:
    """Write a session preset JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": SESSION_JSON_VERSION,
        "primary_path": session.primary_path,
        "compare_path": session.compare_path,
        "active_slot": session.active_slot,
        "compare_enabled": session.compare_enabled,
        "compare_visible_in_scene": session.compare_visible_in_scene,
        "thick_all_spins_in_scene": session.thick_all_spins_in_scene,
        "mode": session.mode,
        "acquisition_index": session.acquisition_index,
        "frame_index": session.frame_index,
        "fps": session.fps,
        "loop": session.loop,
        "selected_delta_f_hz": session.selected_delta_f_hz,
        "bookmarks_hz": session.normalized_bookmarks(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_session_json(path: Path) -> SessionState:
    """Load and validate a session preset JSON file."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        msg = f"Invalid session JSON: {path}"
        raise ValueError(msg) from exc

    if not isinstance(raw, dict):
        msg = "Session JSON root must be an object."
        raise ValueError(msg)

    version = raw.get("version")
    if version != SESSION_JSON_VERSION:
        msg = f"Unsupported session JSON version: {version!r}"
        raise ValueError(msg)

    try:
        return SessionState(
            primary_path=_optional_string(raw.get("primary_path")),
            compare_path=_optional_string(raw.get("compare_path")),
            active_slot=str(raw["active_slot"]),
            compare_enabled=bool(raw.get("compare_enabled", False)),
            compare_visible_in_scene=bool(raw.get("compare_visible_in_scene", True)),
            thick_all_spins_in_scene=bool(raw.get("thick_all_spins_in_scene", False)),
            mode=str(raw["mode"]),
            acquisition_index=int(raw.get("acquisition_index", 0)),
            frame_index=int(raw.get("frame_index", 0)),
            fps=float(raw["fps"]),
            loop=bool(raw.get("loop", True)),
            selected_delta_f_hz=_optional_float(raw.get("selected_delta_f_hz")),
            bookmarks_hz=_float_list(raw.get("bookmarks_hz", [])),
        )
    except KeyError as exc:
        msg = f"Missing required session key: {exc.args[0]}"
        raise ValueError(msg) from exc
    except (TypeError, ValueError) as exc:
        msg = "Invalid session JSON value."
        raise ValueError(msg) from exc


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _float_list(value: Any) -> list[float]:
    if not isinstance(value, list):
        msg = "bookmarks_hz must be a list."
        raise ValueError(msg)
    return [float(item) for item in value]

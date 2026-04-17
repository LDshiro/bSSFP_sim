"""Export service for Chapter 7 screenshot bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QMainWindow, QWidget

from bssfpviz.gui.profile_panel import ProfilePanel
from bssfpviz.gui.scene_panel import ScenePanel
from bssfpviz.gui.session_state import SessionState
from bssfpviz.io.session_json import save_session_json


class ExportService:
    """Write screenshot bundles for the current GUI state."""

    def export_current_view_bundle(
        self,
        output_dir: Path,
        main_window: QMainWindow,
        scene_panel: ScenePanel,
        profile_panel: ProfilePanel,
        time_series_widget: QWidget | None,
        session_state: SessionState,
        notes: dict[str, str] | None = None,
    ) -> Path:
        """Export screenshots and session metadata into one directory."""
        output_dir.mkdir(parents=True, exist_ok=True)

        main_window_path = output_dir / "main_window.png"
        scene_panel_path = output_dir / "scene_panel.png"
        profile_panel_path = output_dir / "profile_panel.png"
        time_series_path = output_dir / "time_series_panel.png"
        session_path = output_dir / "session_state.json"
        manifest_path = output_dir / "manifest.json"

        main_window.grab().save(str(main_window_path))
        profile_panel.grab().save(str(profile_panel_path))
        if time_series_widget is not None:
            time_series_widget.grab().save(str(time_series_path))

        try:
            scene_panel.save_screenshot(scene_panel_path)
        except Exception:  # noqa: BLE001
            scene_panel.grab().save(str(scene_panel_path))

        save_session_json(session_path, session_state)

        files: dict[str, Any] = {
            "main_window": main_window_path.name,
            "scene_panel": scene_panel_path.name,
            "profile_panel": profile_panel_path.name,
            "session_state": session_path.name,
        }
        if time_series_widget is not None:
            files["time_series_panel"] = time_series_path.name

        manifest: dict[str, Any] = {
            "version": 1,
            "generated_by": "bssfpviz",
            "files": files,
        }
        if notes:
            manifest["notes"] = dict(notes)

        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return output_dir

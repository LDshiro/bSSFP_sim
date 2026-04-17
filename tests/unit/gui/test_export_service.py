"""Unit tests for Chapter 7 export bundles."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from bssfpviz.gui.dataset_view_model import DatasetViewModel
from bssfpviz.gui.export_service import ExportService
from bssfpviz.gui.profile_panel import ProfilePanel
from bssfpviz.gui.scene_panel import ScenePanel
from bssfpviz.gui.session_state import SessionState


def test_export_service_writes_bundle(
    monkeypatch: object,
    qapp: object,
    small_simulation_dataset: object,
    tmp_path: Path,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)

    main_window = QMainWindow()
    container = QWidget(main_window)
    layout = QVBoxLayout(container)
    scene_panel = ScenePanel(container)
    profile_panel = ProfilePanel(container)
    scene_panel.set_dataset(vm)
    profile_panel.set_dataset(vm)
    layout.addWidget(scene_panel)
    layout.addWidget(profile_panel)
    main_window.setCentralWidget(container)
    main_window.resize(800, 600)
    main_window.show()
    qapp.processEvents()

    service = ExportService()
    output_dir = tmp_path / "bundle"
    session = SessionState(primary_path="primary.h5", selected_delta_f_hz=0.0)

    written_dir = service.export_current_view_bundle(
        output_dir=output_dir,
        main_window=main_window,
        scene_panel=scene_panel,
        profile_panel=profile_panel,
        time_series_widget=profile_panel.time_series_widget,
        session_state=session,
    )

    assert written_dir == output_dir
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "session_state.json").exists()

    png_files = sorted(output_dir.glob("*.png"))
    assert len(png_files) >= 3

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    assert manifest["files"]["scene_panel"] == "scene_panel.png"

    main_window.close()

"""Integration tests for Chapter 7 compare mode in the main window."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6")

from bssfpviz.gui.main_window import MainWindow
from conftest import build_test_simulation_config, build_test_simulation_dataset


def test_main_window_compare_mode_and_export(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    small_simulation_dataset: object,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    window = MainWindow()
    window.show()
    qapp.processEvents()
    compare_dataset = build_test_simulation_dataset(
        build_test_simulation_config(
            n_rf_samples=6,
            n_cycles=4,
            delta_f_hz=np.array([-30.0, -5.0, 25.0], dtype=np.float64),
        )
    )

    window.set_loaded_dataset(small_simulation_dataset)
    window.set_compare_dataset(compare_dataset)
    qapp.processEvents()

    assert window.comparison_controller.get_active_vm() is not None
    assert window.comparison_controller.get_other_vm() is not None
    assert window.comparison_controller.session_state().compare_enabled is True
    assert "mapped compare:" in window.playback_bar.compare_info_label.text()

    window.comparison_panel.active_slot_combo.setCurrentIndex(1)
    qapp.processEvents()
    assert window.comparison_controller.session_state().active_slot == "compare"
    assert window.playback_bar.active_slot_label.text() == "active: compare"
    assert "mapped primary:" in window.playback_bar.compare_info_label.text()

    window.comparison_panel.compare_enabled_checkbox.setChecked(False)
    qapp.processEvents()
    assert window.comparison_controller.session_state().compare_enabled is False
    assert window.playback_bar.compare_info_label.text() == "compare: disabled"

    export_dir = tmp_path / "compare_bundle"
    monkeypatch.setattr(
        "bssfpviz.gui.main_window.QFileDialog.getExistingDirectory",
        lambda *_args, **_kwargs: str(export_dir),
    )

    window.on_export_current_view_bundle()

    assert (export_dir / "manifest.json").exists()
    assert (export_dir / "session_state.json").exists()
    assert (export_dir / "main_window.png").exists()

    window.close()

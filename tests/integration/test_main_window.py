"""Integration tests for the Chapter 7 main window."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pytest
from PySide6.QtWidgets import QToolBar

pytest.importorskip("PySide6")

from bssfpviz.gui.main_window import MainWindow


def test_main_window_boots_headless(monkeypatch: pytest.MonkeyPatch, qapp: object) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    window = MainWindow()
    window.show()

    assert window.windowTitle() == "Bloch / bSSFP Visualizer - Chapter 7"
    assert window.config_editor is not None
    assert window.scene_panel is not None
    assert window.profile_panel is not None
    assert window.metadata_panel is not None
    assert window.log_panel is not None

    window.close()


def test_main_window_has_menu_and_toolbar_actions(
    monkeypatch: pytest.MonkeyPatch, qapp: object
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    window = MainWindow()

    assert window.findChild(type(window.new_config_action), "action-new-config") is not None
    assert window.findChild(type(window.run_compute_action), "action-run-compute") is not None
    assert window.findChild(type(window.load_config_action), "action-load-config") is not None
    assert window.findChild(type(window.save_config_action), "action-save-config") is not None
    assert window.findChild(type(window.open_hdf5_action), "action-open-hdf5") is not None
    assert (
        window.findChild(type(window.open_compare_dataset_action), "action-open-compare-dataset")
        is not None
    )
    assert (
        window.findChild(type(window.open_generic_preview_action), "action-open-generic-preview")
        is not None
    )
    assert window.findChild(QToolBar, "main-toolbar") is not None

    window.close()


def test_main_window_load_dataset_updates_panels(
    monkeypatch: pytest.MonkeyPatch, qapp: object, tmp_path: Path
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    window = MainWindow()
    hdf5_path = tmp_path / "window_fixture.h5"
    _write_gui_fixture_hdf5(hdf5_path)

    window.load_dataset_from_path(hdf5_path)

    assert "window_fixture" in window.metadata_panel.text_edit.toPlainText()
    assert window.profile_panel._last_curve_count == 3
    assert str(hdf5_path) in window.loaded_file_label.text()
    assert window.playback_bar.frame_slider.isEnabled() is True

    window.close()


def test_main_window_run_action_toggles_enabled_state(
    monkeypatch: pytest.MonkeyPatch, qapp: object, tmp_path: Path
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    window = MainWindow()
    output_path = tmp_path / "run_result.h5"
    observed: dict[str, bool] = {}

    def fake_save_dialog(*_args: object, **_kwargs: object) -> tuple[str, str]:
        return (str(output_path), "HDF5 Files (*.h5)")

    def fake_start_compute_worker(config: object, path: Path) -> None:
        _write_gui_fixture_hdf5(path)
        observed["run_disabled_during_start"] = not window.run_compute_action.isEnabled()
        observed["button_disabled_during_start"] = not window.config_editor.run_button.isEnabled()
        window.on_compute_finished(SimpleNamespace(case_name=config.meta.case_name), path)

    monkeypatch.setattr("bssfpviz.gui.main_window.QFileDialog.getSaveFileName", fake_save_dialog)
    monkeypatch.setattr(window, "_start_compute_worker", fake_start_compute_worker)

    window.on_run_compute()

    assert observed["run_disabled_during_start"] is True
    assert observed["button_disabled_during_start"] is True
    assert window.run_compute_action.isEnabled() is True
    assert window.config_editor.run_button.isEnabled() is True
    assert output_path.exists()

    window.close()


def test_main_window_opens_generic_preview_window(
    monkeypatch: pytest.MonkeyPatch, qapp: object
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    window = MainWindow()
    window.show()
    qapp.processEvents()

    window.on_open_generic_preview()
    qapp.processEvents()

    assert window._generic_preview_window is not None
    assert window._generic_preview_window.isVisible() is True
    assert window._generic_preview_window.windowTitle() == "Generic Sequence Preview"

    window._generic_preview_window.close()
    window.close()


def _write_gui_fixture_hdf5(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as handle:
        handle.attrs["schema_version"] = "2.0"
        handle.attrs["created_at_utc"] = "2026-03-28T00:00:00Z"
        handle.attrs["app_name"] = "bloch-ssfp-visualizer"
        handle.attrs["app_version"] = "0.5.0"
        handle.attrs["git_commit"] = "unknown"

        handle.create_dataset("/meta/case_name", data="window_fixture", dtype=h5py.string_dtype())
        handle.create_dataset("/meta/description", data="window test", dtype=h5py.string_dtype())

        handle.create_dataset("/config/physics/T1_s", data=1.5)
        handle.create_dataset("/config/physics/T2_s", data=1.0)
        handle.create_dataset("/config/physics/M0", data=1.0)
        handle.create_dataset("/config/sequence/TR_s", data=0.004)
        handle.create_dataset("/config/sequence/rf_duration_s", data=0.001)
        handle.create_dataset("/config/sequence/n_rf", data=16)
        handle.create_dataset("/config/sequence/alpha_deg", data=45.0)
        handle.create_dataset("/config/sequence/readout_fraction_of_free", data=0.5)
        handle.create_dataset(
            "/config/phase_cycles/values_deg",
            data=np.array([[0.0, 0.0], [0.0, 180.0]], dtype=np.float64),
        )

        handle.create_dataset("/sweep/delta_f_hz", data=np.array([-10.0, 0.0, 10.0]))
        handle.create_dataset("/rk/time_s", data=np.array([0.0, 1.0e-3]))
        handle.create_dataset("/rk/M", data=np.ones((3, 2, 2, 3), dtype=np.float64))
        handle.create_dataset("/steady_state/orbit_time_s", data=np.array([0.0, 2.0e-3, 4.0e-3]))
        handle.create_dataset("/steady_state/orbit_M", data=np.ones((3, 2, 3, 3), dtype=np.float64))
        handle.create_dataset(
            "/steady_state/fixed_points", data=np.ones((3, 2, 3), dtype=np.float64)
        )
        handle.create_dataset(
            "/profiles/individual_complex_realimag",
            data=np.array(
                [
                    [[1.0, 0.0], [0.0, 1.0]],
                    [[2.0, 0.0], [1.0, 1.0]],
                    [[3.0, 0.0], [1.0, 2.0]],
                ],
                dtype=np.float64,
            ),
        )
        handle.create_dataset(
            "/profiles/individual_abs",
            data=np.array([[1.0, 1.0], [2.0, np.sqrt(2.0)], [3.0, np.sqrt(5.0)]], dtype=np.float64),
        )
        handle.create_dataset(
            "/profiles/sos_abs",
            data=np.array([np.sqrt(2.0), np.sqrt(6.0), np.sqrt(14.0)], dtype=np.float64),
        )

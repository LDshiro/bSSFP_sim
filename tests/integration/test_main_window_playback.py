"""Integration tests for Chapter 6 playback wiring in the main window."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

pytest.importorskip("PySide6")

from bssfpviz.gui.main_window import MainWindow


def test_main_window_sets_loaded_dataset_and_syncs_playback(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    window = MainWindow()
    window.set_loaded_dataset(small_simulation_dataset)
    qapp.processEvents()

    assert window._current_view_model is not None
    assert window.playback_bar.frame_slider.isEnabled() is True

    metadata_refreshes = 0
    original_set_comparison_state = window.metadata_panel.set_comparison_state

    def counted_set_comparison_state(*args: object, **kwargs: object) -> None:
        nonlocal metadata_refreshes
        metadata_refreshes += 1
        original_set_comparison_state(*args, **kwargs)

    monkeypatch.setattr(window.metadata_panel, "set_comparison_state", counted_set_comparison_state)

    window.playback_bar.frame_slider.setValue(2)
    qapp.processEvents()

    state = window.playback_controller.state()
    assert state.frame_index == 2
    assert np.isclose(
        window.profile_panel._time_marker_x,
        window._current_view_model.get_current_time_s(state.mode, 2),
    )
    assert window.playback_bar.active_slot_label.text() == "active: primary"
    assert window.playback_bar.compare_info_label.text() == "compare: disabled"
    assert window.scene_panel._placeholder_label is not None
    assert "frame:" in window.scene_panel._placeholder_label.text()
    assert metadata_refreshes == 0

    window.playback_bar.acq_combo.setCurrentIndex(1)
    qapp.processEvents()
    assert window.playback_controller.state().acquisition_index == 1
    assert metadata_refreshes == 1

    window.playback_bar.mode_combo.setCurrentIndex(1)
    qapp.processEvents()
    assert window.playback_controller.state().mode == "steady"

    window.close()


def test_main_window_load_dataset_from_path_prefers_dense_alias_frames(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    window = MainWindow()
    hdf5_path = tmp_path / "dense_alias_fixture.h5"
    _write_dense_alias_fixture_hdf5(hdf5_path)

    window.load_dataset_from_path(hdf5_path)
    qapp.processEvents()

    assert window._current_view_model is not None
    assert window._current_view_model.n_reference_frames == 4
    assert window._current_view_model.n_steady_frames == 5
    assert window.playback_bar.active_slot_label.text() == "active: primary"

    window.playback_bar.mode_combo.setCurrentIndex(1)
    qapp.processEvents()

    assert window.playback_controller.state().mode == "steady"
    assert window.playback_bar.frame_slider.maximum() == 4

    window.close()


def _write_dense_alias_fixture_hdf5(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as handle:
        handle.attrs["schema_version"] = "2.0"
        handle.attrs["created_at_utc"] = "2026-03-31T00:00:00Z"
        handle.attrs["app_name"] = "bloch-ssfp-visualizer"
        handle.attrs["app_version"] = "0.7.1"
        handle.attrs["git_commit"] = "unknown"

        handle.create_dataset(
            "/meta/case_name", data="dense_alias_fixture", dtype=h5py.string_dtype()
        )
        handle.create_dataset(
            "/meta/description", data="dense alias playback test", dtype=h5py.string_dtype()
        )
        handle.create_dataset("/meta/run_name", data="canonical_fixture", dtype=h5py.string_dtype())
        handle.create_dataset(
            "/meta/user_notes", data="canonical playback test", dtype=h5py.string_dtype()
        )

        handle.create_dataset("/config/physics/T1_s", data=1.5)
        handle.create_dataset("/config/physics/T2_s", data=1.0)
        handle.create_dataset("/config/physics/M0", data=1.0)
        handle.create_dataset("/config/physics/gamma_rad_per_s_per_T", data=267522187.44)
        handle.create_dataset("/config/sequence/TR_s", data=0.004)
        handle.create_dataset("/config/sequence/TE_s", data=0.0025)
        handle.create_dataset("/config/sequence/rf_duration_s", data=0.001)
        handle.create_dataset("/config/sequence/free_duration_s", data=0.003)
        handle.create_dataset("/config/sequence/n_rf", data=16)
        handle.create_dataset("/config/sequence/n_rf_samples", data=16)
        handle.create_dataset("/config/sequence/alpha_deg", data=45.0)
        handle.create_dataset("/config/sequence/flip_angle_rad", data=np.pi / 4.0)
        handle.create_dataset("/config/sequence/readout_fraction_of_free", data=0.5)
        handle.create_dataset("/config/sequence/n_cycles", data=1)
        handle.create_dataset(
            "/config/phase_cycles/values_deg",
            data=np.array([[0.0, 0.0], [0.0, 180.0]], dtype=np.float64),
        )
        handle.create_dataset(
            "/config/sequence/phase_schedule_rad",
            data=np.array([[0.0, 0.0], [0.0, np.pi]], dtype=np.float64),
        )
        handle.create_dataset("/sweep/delta_f_hz", data=np.array([-10.0, 0.0, 10.0]))
        handle.create_dataset("/config/sampling/delta_f_hz", data=np.array([-10.0, 0.0, 10.0]))
        handle.create_dataset("/config/sampling/rk_dt_s", data=1.0e-4)
        handle.create_dataset("/config/sampling/steady_state_dt_s", data=1.0e-4)
        handle.create_dataset("/config/sampling/n_reference_steps", data=2)
        handle.create_dataset("/config/sampling/n_steady_state_steps", data=3)
        handle.create_dataset("/waveforms/rf_xy", data=np.zeros((16, 2), dtype=np.float64))

        handle.create_dataset("/rk/time_s", data=np.array([0.0, 1.0e-3, 2.0e-3, 4.0e-3]))
        handle.create_dataset("/rk/M", data=np.ones((3, 2, 4, 3), dtype=np.float64))
        handle.create_dataset(
            "/steady_state/orbit_time_s",
            data=np.array([0.0, 1.0e-3, 2.0e-3, 3.0e-3, 4.0e-3]),
        )
        handle.create_dataset("/steady_state/orbit_M", data=np.ones((3, 2, 5, 3), dtype=np.float64))
        handle.create_dataset(
            "/steady_state/fixed_points", data=np.ones((3, 2, 3), dtype=np.float64)
        )

        handle.create_dataset(
            "/time/reference_time_s", data=np.array([0.0, 4.0e-3], dtype=np.float64)
        )
        handle.create_dataset(
            "/time/steady_state_time_s",
            data=np.array([0.0, 2.0e-3, 4.0e-3], dtype=np.float64),
        )
        handle.create_dataset("/reference/M_xyz", data=np.full((2, 3, 2, 3), 7.0, dtype=np.float64))
        handle.create_dataset(
            "/steady_state/orbit_xyz", data=np.full((2, 3, 3, 3), 9.0, dtype=np.float64)
        )
        handle.create_dataset(
            "/steady_state/fixed_point_xyz",
            data=np.full((2, 3, 3), 11.0, dtype=np.float64),
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
            "/profiles/individual_complex",
            data=np.array(
                [
                    [1.0 + 0.0j, 2.0 + 0.0j, 3.0 + 0.0j],
                    [0.0 + 1.0j, 1.0 + 1.0j, 1.0 + 2.0j],
                ],
                dtype=np.complex128,
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
        handle.create_dataset(
            "/profiles/sos_magnitude",
            data=np.array([np.sqrt(2.0), np.sqrt(6.0), np.sqrt(14.0)], dtype=np.float64),
        )

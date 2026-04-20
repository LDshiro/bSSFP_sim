"""Tests for the Chapter 5 adapter layer."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np

from bssfpviz.gui.adapters import (
    dataset_to_view_model,
    load_hdf5_dataset,
    load_run_config_from_yaml,
)


def test_load_run_config_adapter_reads_yaml() -> None:
    config = load_run_config_from_yaml(Path("examples/configs/chapter5_default.yaml"))

    assert config.meta.case_name == "chapter5_default"
    assert config.sequence.waveform_kind == "hann"
    assert config.phase_cycles.values_deg.shape == (2, 2)
    assert config.integration.rk_method == "PROPAGATOR"


def test_load_hdf5_dataset_adapter_returns_gui_view(tmp_path: Path) -> None:
    hdf5_path = tmp_path / "adapter_fixture.h5"
    _write_gui_fixture_hdf5(hdf5_path)

    dataset = load_hdf5_dataset(hdf5_path)

    assert dataset.delta_f_hz is not None
    assert dataset.rk_magnetization is not None
    assert dataset.rk_magnetization.shape == (3, 2, 4, 3)
    assert dataset.meta["case_name"] == "adapter_fixture"
    assert dataset.steady_state_time_s is not None
    assert dataset.steady_state_time_s.shape == (5,)


def test_load_hdf5_dataset_adapter_exposes_profile_magnitude(tmp_path: Path) -> None:
    hdf5_path = tmp_path / "adapter_fixture.h5"
    _write_gui_fixture_hdf5(hdf5_path)

    dataset = load_hdf5_dataset(hdf5_path)
    magnitude = dataset.individual_profile_magnitude

    assert magnitude is not None
    np.testing.assert_allclose(
        magnitude,
        np.array(
            [
                [1.0, 1.0],
                [2.0, np.sqrt(2.0)],
                [3.0, np.sqrt(5.0)],
            ],
            dtype=np.float64,
        ),
    )


def test_dataset_to_view_model_normalizes_alias_dataset(tmp_path: Path) -> None:
    hdf5_path = tmp_path / "adapter_fixture.h5"
    _write_gui_fixture_hdf5(hdf5_path)

    dataset = load_hdf5_dataset(hdf5_path)
    vm = dataset_to_view_model(dataset)

    assert vm.n_spins == 3
    assert vm.n_acq == 2
    assert vm.n_reference_frames == 4
    assert vm.n_steady_frames == 5
    assert vm.get_vectors_xyz("reference", 0, 0).shape == (3, 3)
    assert vm.get_vectors_xyz("steady", 0, 0).shape == (3, 3)


def _write_gui_fixture_hdf5(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as handle:
        handle.attrs["schema_version"] = "2.0"
        handle.attrs["created_at_utc"] = "2026-03-28T00:00:00Z"
        handle.attrs["app_name"] = "bloch-ssfp-visualizer"
        handle.attrs["app_version"] = "0.5.0"
        handle.attrs["git_commit"] = "unknown"

        handle.create_dataset("/meta/case_name", data="adapter_fixture", dtype=h5py.string_dtype())
        handle.create_dataset("/meta/description", data="adapter test", dtype=h5py.string_dtype())
        handle.create_dataset("/meta/run_name", data="canonical_fixture", dtype=h5py.string_dtype())
        handle.create_dataset(
            "/meta/user_notes", data="canonical adapter test", dtype=h5py.string_dtype()
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
            "/time/steady_state_time_s", data=np.array([0.0, 2.0e-3, 4.0e-3], dtype=np.float64)
        )
        handle.create_dataset("/reference/M_xyz", data=np.full((2, 3, 2, 3), 7.0, dtype=np.float64))
        handle.create_dataset(
            "/steady_state/orbit_xyz",
            data=np.full((2, 3, 3, 3), 9.0, dtype=np.float64),
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

"""Integration tests for the Chapter 4 compute CLI."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from textwrap import dedent

import h5py
import numpy as np
import pytest

from bssfpviz.io.hdf5_store import load_dataset
from bssfpviz.models.run_config import RunConfig
from bssfpviz.workflows.compute_cli import main
from bssfpviz.workflows.run_compute import run_compute

bssfp_runner_module = importlib.import_module("bssfpviz.sequences.bssfp.runner")


def test_compute_cli_generates_hdf5_and_summary_json(tmp_path: Path) -> None:
    config_path = tmp_path / "small_compute.yaml"
    output_path = tmp_path / "small_compute.h5"
    summary_json_path = tmp_path / "small_compute_summary.json"
    config_path.write_text(_small_config_text(), encoding="utf-8")

    exit_code = main(
        [
            "--config",
            str(config_path),
            "--output",
            str(output_path),
            "--summary-json",
            str(summary_json_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert summary_json_path.exists()

    with h5py.File(output_path, "r") as handle:
        assert "/profiles/sos_abs" in handle
        assert "/rk/M" in handle
        assert "/steady_state/orbit_time_s" in handle
        assert "/steady_state/orbit_M" in handle
        assert handle["/profiles/sos_abs"].shape == (3,)
        assert handle["/rk/M"].shape[:3] == (3, 2, handle["/rk/time_s"].shape[0])
        assert handle["/steady_state/orbit_M"].shape[:3] == (
            3,
            2,
            handle["/steady_state/orbit_time_s"].shape[0],
        )
        assert handle["/steady_state/orbit_time_s"].shape[0] > (2 * 16 + 3)
        assert handle["/waveforms/base_xy"].shape == (16, 2)
        assert handle["/waveforms/per_acquisition_xy"].shape == (2, 2, 16, 2)

    summary_data = json.loads(summary_json_path.read_text(encoding="utf-8"))
    assert summary_data["case_name"] == "chapter4_small"
    assert summary_data["n_delta_f"] == 3
    assert summary_data["n_acquisitions"] == 2
    assert summary_data["n_time_samples"] > 0

    loaded = load_dataset(output_path)
    assert loaded.reference_m_xyz.shape[0:2] == (2, 3)
    assert loaded.steady_state_time_s.shape[0] == (2 * 16 + 3)


def test_compute_cli_requires_overwrite_for_existing_output(tmp_path: Path) -> None:
    config_path = tmp_path / "small_compute.yaml"
    output_path = tmp_path / "small_compute.h5"
    config_path.write_text(_small_config_text(), encoding="utf-8")
    output_path.write_text("already exists", encoding="utf-8")

    exit_code = main(["--config", str(config_path), "--output", str(output_path)])

    assert exit_code != 0


def test_compute_cli_overwrites_existing_output_when_requested(tmp_path: Path) -> None:
    config_path = tmp_path / "small_compute.yaml"
    output_path = tmp_path / "small_compute.h5"
    config_path.write_text(_small_config_text(), encoding="utf-8")
    output_path.write_text("already exists", encoding="utf-8")

    exit_code = main(
        ["--config", str(config_path), "--output", str(output_path), "--overwrite", "--quiet"]
    )

    assert exit_code == 0
    with h5py.File(output_path, "r") as handle:
        assert "/profiles/sos_abs" in handle


def test_run_compute_uses_fast_reference_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "small_compute.yaml"
    output_path = tmp_path / "small_compute.h5"
    config_path.write_text(_small_config_text(rk_method="PROPAGATOR"), encoding="utf-8")
    config = RunConfig.from_yaml(config_path)
    loop_count = config.sweep.count * config.n_acquisitions
    calls = {"affine": 0, "grid": 0}

    real_affine = bssfp_runner_module.integrate_reference_trajectory_with_affine_grid
    real_grid = bssfp_runner_module.integrate_reference_trajectory_with_grid

    def counting_affine(*args: object, **kwargs: object) -> object:
        calls["affine"] += 1
        return real_affine(*args, **kwargs)

    def counting_grid(*args: object, **kwargs: object) -> object:
        calls["grid"] += 1
        return real_grid(*args, **kwargs)

    monkeypatch.setattr(
        bssfp_runner_module,
        "integrate_reference_trajectory_with_affine_grid",
        counting_affine,
    )
    monkeypatch.setattr(
        bssfp_runner_module,
        "integrate_reference_trajectory_with_grid",
        counting_grid,
    )

    summary = run_compute(config, output_path)

    assert summary.n_time_samples > 0
    assert calls["grid"] == 0
    assert calls["affine"] == 2 * loop_count
    with h5py.File(output_path, "r") as handle:
        assert handle["/rk/M"].shape[2] == summary.n_time_samples


def test_run_compute_uses_rk45_reference_path_when_requested(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "small_compute_rk45.yaml"
    output_path = tmp_path / "small_compute_rk45.h5"
    config_path.write_text(_small_config_text(rk_method="RK45"), encoding="utf-8")
    config = RunConfig.from_yaml(config_path)
    loop_count = config.sweep.count * config.n_acquisitions
    calls = {"affine": 0, "grid": 0}

    real_affine = bssfp_runner_module.integrate_reference_trajectory_with_affine_grid
    real_grid = bssfp_runner_module.integrate_reference_trajectory_with_grid

    def counting_affine(*args: object, **kwargs: object) -> object:
        calls["affine"] += 1
        return real_affine(*args, **kwargs)

    def counting_grid(*args: object, **kwargs: object) -> object:
        calls["grid"] += 1
        return real_grid(*args, **kwargs)

    monkeypatch.setattr(
        bssfp_runner_module,
        "integrate_reference_trajectory_with_affine_grid",
        counting_affine,
    )
    monkeypatch.setattr(
        bssfp_runner_module,
        "integrate_reference_trajectory_with_grid",
        counting_grid,
    )

    summary = run_compute(config, output_path)

    assert summary.n_time_samples > 0
    assert calls["grid"] == loop_count
    assert calls["affine"] == loop_count
    with h5py.File(output_path, "r") as handle:
        assert handle["/rk/M"].shape[2] == summary.n_time_samples


def test_run_compute_keeps_reference_grid_when_switching_methods(tmp_path: Path) -> None:
    propagator_config_path = tmp_path / "small_compute_propagator.yaml"
    rk45_config_path = tmp_path / "small_compute_rk45.yaml"
    propagator_output_path = tmp_path / "small_compute_propagator.h5"
    rk45_output_path = tmp_path / "small_compute_rk45.h5"

    propagator_config_path.write_text(_small_config_text(rk_method="PROPAGATOR"), encoding="utf-8")
    rk45_config_path.write_text(_small_config_text(rk_method="RK45"), encoding="utf-8")

    propagator_config = RunConfig.from_yaml(propagator_config_path)
    rk45_config = RunConfig.from_yaml(rk45_config_path)

    run_compute(propagator_config, propagator_output_path)
    run_compute(rk45_config, rk45_output_path)

    with h5py.File(propagator_output_path, "r") as propagator_handle, h5py.File(
        rk45_output_path, "r"
    ) as rk45_handle:
        np.testing.assert_allclose(propagator_handle["/rk/time_s"][:], rk45_handle["/rk/time_s"][:])
        assert propagator_handle["/rk/M"].shape == rk45_handle["/rk/M"].shape
        np.testing.assert_allclose(
            propagator_handle["/steady_state/orbit_time_s"][:],
            rk45_handle["/steady_state/orbit_time_s"][:],
        )


def _small_config_text(*, rk_method: str = "PROPAGATOR") -> str:
    return dedent(
        """
        meta:
          case_name: "chapter4_small"
          description: "small integration-test case"

        physics:
          T1_s: 1.5
          T2_s: 1.0
          M0: 1.0

        sequence:
          TR_s: 0.004
          rf_duration_s: 0.001
          n_rf: 16
          alpha_deg: 45.0
          waveform_kind: "rect"
          readout_fraction_of_free: 0.5

        phase_cycles:
          values_deg:
            - [0.0, 0.0]
            - [0.0, 180.0]

        sweep:
          delta_f_hz:
            start: -50.0
            stop: 50.0
            count: 3

        integration:
          rk_method: "{rk_method}"
          rk_rtol: 1.0e-6
          rk_atol: 1.0e-8
          rk_max_step_s: 1.0e-4
          rk_superperiods: 2
          save_every_time_step: true

        output:
          save_profiles: true
          save_rk_trajectories: true
          save_steady_state_orbit: true
          save_fixed_points: true
        """
    ).format(rk_method=rk_method).strip()

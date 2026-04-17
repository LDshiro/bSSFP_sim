"""Unit tests for the fast affine-grid reference integrator."""

from __future__ import annotations

import numpy as np

from bssfpviz.core.reference import (
    build_affine_reference_grid_spec,
    integrate_reference_trajectory,
    integrate_reference_trajectory_with_affine_grid,
    integrate_reference_trajectory_with_grid,
)
from bssfpviz.core.segments import (
    build_superperiod_segments,
    make_base_rf_waveform,
    materialize_actual_waveforms,
)
from bssfpviz.workflows.compute_dataset import compute_dataset


def test_affine_grid_reference_matches_rk45_on_shared_grid(
    small_simulation_config: object,
) -> None:
    base_rf_xy = make_base_rf_waveform(small_simulation_config.sequence)
    actual_rf_xy = materialize_actual_waveforms(
        base_rf_xy, small_simulation_config.sequence.phase_schedule_rad
    )
    delta_omega_rad_s = float(small_simulation_config.sampling.delta_omega_rad_s[1])
    segments = build_superperiod_segments(
        actual_rf_xy=actual_rf_xy[0],
        delta_omega_rad_s=delta_omega_rad_s,
        config=small_simulation_config,
    )
    n_superperiods = 3
    max_step_s = 1.0e-4
    t_eval = _build_repeated_subdivision_grid(
        segments.boundary_time_s,
        n_superperiods=n_superperiods,
        max_step_s=max_step_s,
    )
    grid_spec = build_affine_reference_grid_spec(
        boundary_time_s=segments.boundary_time_s,
        total_duration_s=n_superperiods * float(segments.boundary_time_s[-1]),
        t_eval=t_eval,
    )

    t_rk, m_rk = integrate_reference_trajectory_with_grid(
        boundary_time_s=segments.boundary_time_s,
        segment_ux=segments.segment_ux,
        segment_uy=segments.segment_uy,
        delta_omega_rad_s=delta_omega_rad_s,
        total_duration_s=n_superperiods * float(segments.boundary_time_s[-1]),
        physics=small_simulation_config.physics,
        t_eval=t_eval,
        method="RK45",
        rtol=1.0e-9,
        atol=1.0e-11,
        max_step_s=max_step_s,
        initial_state=np.asarray([0.0, 0.0, small_simulation_config.physics.m0], dtype=np.float64),
    )
    t_fast, m_fast = integrate_reference_trajectory_with_affine_grid(
        boundary_time_s=segments.boundary_time_s,
        segment_ux=segments.segment_ux,
        segment_uy=segments.segment_uy,
        delta_omega_rad_s=delta_omega_rad_s,
        physics=small_simulation_config.physics,
        grid_spec=grid_spec,
        initial_state=np.asarray([0.0, 0.0, small_simulation_config.physics.m0], dtype=np.float64),
    )

    np.testing.assert_allclose(t_fast, t_eval)
    np.testing.assert_allclose(t_rk, t_eval)
    np.testing.assert_allclose(m_fast, m_rk, atol=5.0e-7, rtol=5.0e-6)


def test_compute_dataset_reference_matches_rk45_on_boundary_grid(
    small_simulation_config: object,
) -> None:
    dataset = compute_dataset(small_simulation_config)
    base_rf_xy = make_base_rf_waveform(small_simulation_config.sequence)
    actual_rf_xy = materialize_actual_waveforms(
        base_rf_xy, small_simulation_config.sequence.phase_schedule_rad
    )
    acquisition_index = 0
    spin_index = 1
    delta_omega_rad_s = float(small_simulation_config.sampling.delta_omega_rad_s[spin_index])

    t_rk, m_rk = integrate_reference_trajectory(
        actual_rf_xy_for_one_acq=actual_rf_xy[acquisition_index],
        delta_omega_rad_s=delta_omega_rad_s,
        config=small_simulation_config,
        physics=small_simulation_config.physics,
    )

    np.testing.assert_allclose(dataset.reference_time_s, t_rk)
    np.testing.assert_allclose(
        dataset.reference_m_xyz[acquisition_index, spin_index],
        m_rk,
        atol=2.0e-6,
        rtol=2.0e-5,
    )


def _build_repeated_subdivision_grid(
    boundary_time_s: np.ndarray,
    *,
    n_superperiods: int,
    max_step_s: float,
) -> np.ndarray:
    superperiod_samples = [0.0]
    current_time_s = 0.0
    segment_dt_s = np.diff(boundary_time_s)

    for dt_s in segment_dt_s:
        n_substeps = max(1, int(np.ceil(float(dt_s) / max_step_s)))
        local_points = current_time_s + np.linspace(
            float(dt_s) / n_substeps,
            float(dt_s),
            n_substeps,
            dtype=np.float64,
        )
        superperiod_samples.extend(local_points.tolist())
        current_time_s += float(dt_s)

    superperiod_time_s = np.asarray(superperiod_samples, dtype=np.float64)
    tiled = [superperiod_time_s]
    for superperiod_index in range(1, n_superperiods):
        tiled.append(
            superperiod_time_s[1:] + float(superperiod_index) * float(superperiod_time_s[-1])
        )
    return np.concatenate(tiled)

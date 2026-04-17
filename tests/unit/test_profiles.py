"""Unit tests for Chapter 3 waveforms, orbit closure, and profile identities."""

from __future__ import annotations

import numpy as np

from bssfpviz.core.propagators import compose_affine_sequence
from bssfpviz.core.segments import (
    build_superperiod_segments,
    make_base_rf_waveform,
    materialize_actual_waveforms,
)
from bssfpviz.core.steady_state import reconstruct_orbit, solve_fixed_point


def test_base_rf_waveform_integrates_to_flip_angle(small_simulation_config: object) -> None:
    rf_xy = make_base_rf_waveform(small_simulation_config.sequence)
    dt_rf = (
        small_simulation_config.sequence.rf_duration_s
        / small_simulation_config.sequence.n_rf_samples
    )

    assert rf_xy.shape == (small_simulation_config.sequence.n_rf_samples, 2)
    np.testing.assert_allclose(
        np.sum(rf_xy[:, 0] * dt_rf), small_simulation_config.sequence.flip_angle_rad
    )
    np.testing.assert_allclose(rf_xy[:, 1], 0.0)


def test_materialize_actual_waveforms_matches_rotation_formula() -> None:
    base_rf_xy = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
    phase_schedule_rad = np.array([[0.0, np.pi / 2.0]], dtype=np.float64)

    actual_rf_xy = materialize_actual_waveforms(base_rf_xy, phase_schedule_rad)

    expected_pulse0 = base_rf_xy
    expected_pulse1 = np.array([[-2.0, 1.0], [-4.0, 3.0]], dtype=np.float64)
    np.testing.assert_allclose(actual_rf_xy[0, 0], expected_pulse0)
    np.testing.assert_allclose(actual_rf_xy[0, 1], expected_pulse1)


def test_reconstruct_orbit_returns_to_fixed_point(small_simulation_config: object) -> None:
    base_rf_xy = make_base_rf_waveform(small_simulation_config.sequence)
    actual_rf_xy = materialize_actual_waveforms(
        base_rf_xy, small_simulation_config.sequence.phase_schedule_rad
    )
    delta_omega_rad_s = float(2.0 * np.pi * small_simulation_config.sampling.delta_f_hz[1])
    segments = build_superperiod_segments(
        actual_rf_xy[0], delta_omega_rad_s, small_simulation_config
    )
    phi3, c3, f_list, g_list = compose_affine_sequence(
        segments.segment_dt_s,
        segments.segment_ux,
        segments.segment_uy,
        delta_omega_rad_s,
        small_simulation_config.physics,
    )
    m0_ss = solve_fixed_point(phi3, c3)
    orbit_xyz = reconstruct_orbit(m0_ss, f_list, g_list, segments.boundary_time_s)

    np.testing.assert_allclose(orbit_xyz[0], orbit_xyz[-1], atol=1e-10, rtol=1e-10)


def test_compute_dataset_preserves_sos_identity(small_computed_dataset: object) -> None:
    dataset = small_computed_dataset
    expected_sos = np.sqrt(np.sum(np.abs(dataset.individual_profile_complex) ** 2, axis=0))

    np.testing.assert_allclose(dataset.sos_profile_magnitude, expected_sos)

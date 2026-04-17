"""Fixed-point and readout computations for one 2TR superperiod."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from bssfpviz.core.propagators import compose_affine_sequence, segment_affine_propagator
from bssfpviz.models.config import SimulationConfig

FloatArray = npt.NDArray[np.float64]


def solve_fixed_point(phi3: FloatArray, c3: FloatArray) -> FloatArray:
    """Solve `(I - Phi) @ M0_ss = c` for the superperiod fixed point."""
    phi3 = np.asarray(phi3, dtype=np.float64)
    c3 = np.asarray(c3, dtype=np.float64)
    return np.asarray(np.linalg.solve(np.eye(3, dtype=np.float64) - phi3, c3), dtype=np.float64)


def reconstruct_orbit(
    m0_ss: FloatArray,
    f_list: FloatArray,
    g_list: FloatArray,
    boundary_time_s: FloatArray,
) -> FloatArray:
    """Reconstruct the boundary orbit from the Chapter 3 affine recurrence."""
    m0_ss = np.asarray(m0_ss, dtype=np.float64)
    f_list = np.asarray(f_list, dtype=np.float64)
    g_list = np.asarray(g_list, dtype=np.float64)
    boundary_time_s = np.asarray(boundary_time_s, dtype=np.float64)
    if boundary_time_s.shape != (f_list.shape[0] + 1,):
        msg = "boundary_time_s must align with the segment count."
        raise ValueError(msg)

    orbit_xyz = np.zeros((boundary_time_s.shape[0], 3), dtype=np.float64)
    orbit_xyz[0] = m0_ss
    for index in range(f_list.shape[0]):
        orbit_xyz[index + 1] = f_list[index] @ orbit_xyz[index] + g_list[index]
    return orbit_xyz


def compute_readout_profile(
    m0_ss: FloatArray,
    actual_rf_xy_for_one_acq: FloatArray,
    delta_omega_rad_s: float,
    config: SimulationConfig,
) -> complex:
    """Return `Mx + 1j * My` at the Chapter 3 readout time."""
    m0_ss = np.asarray(m0_ss, dtype=np.float64)
    actual_rf_xy_for_one_acq = np.asarray(actual_rf_xy_for_one_acq, dtype=np.float64)

    n_rf_samples = config.sequence.n_rf_samples
    dt_rf = config.sequence.rf_duration_s / n_rf_samples
    pulse0_dt_s = np.full(n_rf_samples, dt_rf, dtype=np.float64)
    pulse0_ux = np.asarray(actual_rf_xy_for_one_acq[0, :, 0], dtype=np.float64)
    pulse0_uy = np.asarray(actual_rf_xy_for_one_acq[0, :, 1], dtype=np.float64)

    pulse0_phi, pulse0_c, _, _ = compose_affine_sequence(
        segment_dt_s=pulse0_dt_s,
        segment_ux=pulse0_ux,
        segment_uy=pulse0_uy,
        delta_omega_rad_s=delta_omega_rad_s,
        physics=config.physics,
    )
    m_after_pulse0 = pulse0_phi @ m0_ss + pulse0_c

    half_free_f, half_free_g, _ = segment_affine_propagator(
        ux=0.0,
        uy=0.0,
        delta_omega_rad_s=delta_omega_rad_s,
        dt_s=0.5 * config.sequence.free_duration_s,
        physics=config.physics,
    )
    m_ro = half_free_f @ m_after_pulse0 + half_free_g
    return complex(m_ro[0], m_ro[1])

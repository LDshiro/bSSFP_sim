"""Chapter 3 compute workflow that fills SimulationDataset from exact math."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from bssfpviz import __version__
from bssfpviz.core.propagators import compose_affine_sequence
from bssfpviz.core.reference import (
    build_affine_reference_grid_spec,
    integrate_reference_trajectory_with_affine_grid,
)
from bssfpviz.core.segments import (
    build_superperiod_segments,
    make_base_rf_waveform,
    materialize_actual_waveforms,
)
from bssfpviz.core.steady_state import compute_readout_profile, reconstruct_orbit, solve_fixed_point
from bssfpviz.models.config import (
    PhysicsConfig,
    SamplingConfig,
    SequenceConfig,
    SimulationConfig,
    SimulationMetadata,
)
from bssfpviz.models.results import SimulationDataset

ComplexArray = npt.NDArray[np.complex128]
FloatArray = npt.NDArray[np.float64]


def make_chapter3_demo_config() -> SimulationConfig:
    """Return the Chapter 3 fast configuration from the prompt."""
    phase_schedule_rad = np.array([[0.0, 0.0], [0.0, np.pi]], dtype=np.float64)
    n_rf_samples = 100
    n_cycles = 120
    n_steady_state_steps = 2 * n_rf_samples + 3
    n_reference_steps = n_cycles * (n_steady_state_steps - 1) + 1

    return SimulationConfig(
        physics=PhysicsConfig(t1_s=0.040, t2_s=0.020, m0=1.0),
        sequence=SequenceConfig(
            tr_s=0.004,
            te_s=0.0025,
            rf_duration_s=0.001,
            free_duration_s=0.003,
            n_rf_samples=n_rf_samples,
            flip_angle_rad=float(np.pi / 3.0),
            phase_schedule_rad=phase_schedule_rad,
            n_cycles=n_cycles,
        ),
        sampling=SamplingConfig(
            delta_f_hz=np.array([-12.5, 0.0, 12.5], dtype=np.float64),
            rk_dt_s=1.0e-5,
            steady_state_dt_s=1.0e-5,
            n_reference_steps=n_reference_steps,
            n_steady_state_steps=n_steady_state_steps,
        ),
    )


def compute_dataset(config: SimulationConfig) -> SimulationDataset:
    """Compute reference, fixed-point steady orbit, and profiles for one config."""
    base_rf_xy = make_base_rf_waveform(config.sequence)
    actual_rf_xy = materialize_actual_waveforms(base_rf_xy, config.sequence.phase_schedule_rad)

    n_acq = config.n_acquisitions
    n_spins = config.n_spins
    n_reference_time = config.sampling.n_reference_steps
    n_steady_time = config.sampling.n_steady_state_steps

    reference_m_xyz = np.zeros((n_acq, n_spins, n_reference_time, 3), dtype=np.float64)
    steady_state_orbit_xyz = np.zeros((n_acq, n_spins, n_steady_time, 3), dtype=np.float64)
    steady_state_fixed_point_xyz = np.zeros((n_acq, n_spins, 3), dtype=np.float64)
    individual_profile_complex = np.zeros((n_acq, n_spins), dtype=np.complex128)

    reference_time_s: FloatArray | None = None
    steady_state_time_s: FloatArray | None = None

    for acquisition_index in range(n_acq):
        actual_rf_xy_for_one_acq = actual_rf_xy[acquisition_index]
        for spin_index, delta_f_hz in enumerate(config.sampling.delta_f_hz):
            delta_omega_rad_s = float(2.0 * np.pi * delta_f_hz)
            segment_sequence = build_superperiod_segments(
                actual_rf_xy=actual_rf_xy_for_one_acq,
                delta_omega_rad_s=delta_omega_rad_s,
                config=config,
            )
            phi3, c3, f_list, g_list = compose_affine_sequence(
                segment_dt_s=segment_sequence.segment_dt_s,
                segment_ux=segment_sequence.segment_ux,
                segment_uy=segment_sequence.segment_uy,
                delta_omega_rad_s=delta_omega_rad_s,
                physics=config.physics,
            )
            m0_ss = solve_fixed_point(phi3, c3)
            orbit_xyz = reconstruct_orbit(m0_ss, f_list, g_list, segment_sequence.boundary_time_s)
            readout_profile = compute_readout_profile(
                m0_ss=m0_ss,
                actual_rf_xy_for_one_acq=actual_rf_xy_for_one_acq,
                delta_omega_rad_s=delta_omega_rad_s,
                config=config,
            )
            t_ref, m_ref = _integrate_reference_boundary_grid(
                boundary_time_s=segment_sequence.boundary_time_s,
                segment_ux=segment_sequence.segment_ux,
                segment_uy=segment_sequence.segment_uy,
                delta_omega_rad_s=delta_omega_rad_s,
                config=config,
            )

            if reference_time_s is None:
                reference_time_s = t_ref
            if steady_state_time_s is None:
                steady_state_time_s = segment_sequence.boundary_time_s

            reference_m_xyz[acquisition_index, spin_index] = m_ref
            steady_state_orbit_xyz[acquisition_index, spin_index] = orbit_xyz
            steady_state_fixed_point_xyz[acquisition_index, spin_index] = m0_ss
            individual_profile_complex[acquisition_index, spin_index] = readout_profile

    if reference_time_s is None or steady_state_time_s is None:
        msg = "compute_dataset requires at least one acquisition and one spin."
        raise RuntimeError(msg)

    sos_profile_magnitude = np.sqrt(np.sum(np.abs(individual_profile_complex) ** 2, axis=0))
    metadata = SimulationMetadata(
        app_version=__version__,
        run_name="chapter3_demo",
        user_notes="Chapter 3 computed dataset.",
    )
    return SimulationDataset(
        metadata=metadata,
        config=config,
        rf_xy=base_rf_xy,
        reference_time_s=reference_time_s,
        steady_state_time_s=steady_state_time_s,
        reference_m_xyz=reference_m_xyz,
        steady_state_orbit_xyz=steady_state_orbit_xyz,
        steady_state_fixed_point_xyz=steady_state_fixed_point_xyz,
        individual_profile_complex=individual_profile_complex,
        sos_profile_magnitude=sos_profile_magnitude,
    )


def compute_late_cycle_error(dataset: SimulationDataset) -> float:
    """Return the maximum norm between the last RK cycle and the steady orbit."""
    n_steady_time = dataset.steady_state_time_s.shape[0]
    last_cycle_rk = dataset.reference_m_xyz[:, :, -n_steady_time:, :]
    difference = last_cycle_rk - dataset.steady_state_orbit_xyz
    return float(np.max(np.linalg.norm(difference, axis=-1)))


def _integrate_reference_boundary_grid(
    *,
    boundary_time_s: FloatArray,
    segment_ux: FloatArray,
    segment_uy: FloatArray,
    delta_omega_rad_s: float,
    config: SimulationConfig,
) -> tuple[FloatArray, FloatArray]:
    t_eval = _repeat_boundary_grid(boundary_time_s, n_cycles=config.sequence.n_cycles)
    grid_spec = build_affine_reference_grid_spec(
        boundary_time_s=boundary_time_s,
        total_duration_s=config.sequence.n_cycles * config.superperiod_duration_s,
        t_eval=t_eval,
    )
    return integrate_reference_trajectory_with_affine_grid(
        boundary_time_s=boundary_time_s,
        segment_ux=segment_ux,
        segment_uy=segment_uy,
        delta_omega_rad_s=delta_omega_rad_s,
        physics=config.physics,
        grid_spec=grid_spec,
        initial_state=np.asarray([0.0, 0.0, config.physics.m0], dtype=np.float64),
    )


def _repeat_boundary_grid(boundary_time_s: FloatArray, *, n_cycles: int) -> FloatArray:
    period_s = float(boundary_time_s[-1])
    grids = [np.asarray(boundary_time_s, dtype=np.float64)]
    for cycle_index in range(1, n_cycles):
        grids.append(np.asarray(boundary_time_s[1:] + cycle_index * period_s, dtype=np.float64))
    return np.concatenate(grids)

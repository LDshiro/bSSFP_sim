"""bSSFP family runner that emits generic sequence results."""

from __future__ import annotations

from typing import cast

import numpy as np
import numpy.typing as npt

from bssfpviz.core.affine import reconstruct_orbit, solve_fixed_point
from bssfpviz.core.propagators import compose_affine_sequence
from bssfpviz.core.reference import (
    AffineReferenceGridSpec,
    SolveIvpMethod,
    build_affine_reference_grid_spec,
    integrate_reference_trajectory_with_affine_grid,
    integrate_reference_trajectory_with_grid,
)
from bssfpviz.models.comparison import CompiledSequence, SequenceFamily, SimulationResult
from bssfpviz.models.config import PhysicsConfig as CorePhysicsConfig
from bssfpviz.models.run_config import RunConfig
from bssfpviz.sequences.bssfp.sequence import (
    compute_readout_profile,
    make_base_rf_waveform,
    materialize_actual_waveforms,
)

ComplexArray = npt.NDArray[np.complex128]
FloatArray = npt.NDArray[np.float64]
PROFILE_EPSILON = 1.0e-12


def compile_bssfp_sequence(
    actual_rf_xy_for_one_acq: FloatArray,
    config: RunConfig,
    *,
    label: str,
) -> CompiledSequence:
    """Compile one acquisition into a generic event-train representation."""
    segment_dt_s, boundary_time_s = _build_superperiod_timing(config)
    segment_ux, segment_uy = _build_segment_controls(actual_rf_xy_for_one_acq)
    return CompiledSequence(
        sequence_family=SequenceFamily.BSSFP,
        label=label,
        event_dt_s=segment_dt_s,
        event_ux=segment_ux,
        event_uy=segment_uy,
        sample_times_s={
            "boundary_time_s": boundary_time_s,
            "readout_time_s": np.array([config.sequence.readout_time_s], dtype=np.float64),
        },
        family_metadata={
            "waveform_kind": config.sequence.waveform_kind,
            "readout_fraction_of_free": config.sequence.readout_fraction_of_free,
        },
    )


def run_bssfp_simulation(config: RunConfig, *, run_label: str = "bssfp") -> SimulationResult:
    """Run the bSSFP family backend and return a generic SimulationResult."""
    delta_f_hz = config.sweep.build_delta_f_hz()
    phase_cycles_rad = config.phase_cycles.build_values_rad()
    base_rf_xy = make_base_rf_waveform(config.sequence)
    per_acquisition_xy = materialize_actual_waveforms(base_rf_xy, phase_cycles_rad)
    compiled_sequences = [
        compile_bssfp_sequence(per_acquisition_xy[index], config, label=f"{run_label}_acq_{index}")
        for index in range(config.n_acquisitions)
    ]

    boundary_time_s = compiled_sequences[0].sample_times_s["boundary_time_s"]
    segment_dt_s = compiled_sequences[0].event_dt_s
    canonical_reference_time_s = _tile_superperiod_time_grid(
        np.asarray(boundary_time_s, dtype=np.float64),
        config.integration.rk_superperiods,
    )
    dense_superperiod_time_s = _build_superperiod_rk_grid(config, segment_dt_s)
    rk_time_s = _tile_superperiod_time_grid(
        dense_superperiod_time_s,
        config.integration.rk_superperiods,
    )
    reference_boundary_indices = _build_repeated_boundary_indices(
        dense_superperiod_time_s,
        boundary_time_s,
        config.integration.rk_superperiods,
    )
    canonical_orbit_time_s = np.asarray(boundary_time_s, dtype=np.float64)
    orbit_time_s = np.asarray(dense_superperiod_time_s, dtype=np.float64)
    total_duration_s = float(config.integration.rk_superperiods) * float(boundary_time_s[-1])
    reference_grid_spec = build_affine_reference_grid_spec(
        boundary_time_s=boundary_time_s,
        total_duration_s=total_duration_s,
        t_eval=rk_time_s,
    )
    steady_state_grid_spec = build_affine_reference_grid_spec(
        boundary_time_s=boundary_time_s,
        total_duration_s=float(boundary_time_s[-1]),
        t_eval=orbit_time_s,
    )

    n_delta = delta_f_hz.shape[0]
    n_acq = config.n_acquisitions
    n_rk = rk_time_s.shape[0]
    n_canonical_reference = canonical_reference_time_s.shape[0]
    n_canonical_orbit = canonical_orbit_time_s.shape[0]
    n_orbit = orbit_time_s.shape[0]
    rk_m = np.zeros((n_delta, n_acq, n_rk, 3), dtype=np.float64)
    canonical_reference_m = np.zeros((n_delta, n_acq, n_canonical_reference, 3), dtype=np.float64)
    canonical_orbit_m = np.zeros((n_delta, n_acq, n_canonical_orbit, 3), dtype=np.float64)
    orbit_m = np.zeros((n_delta, n_acq, n_orbit, 3), dtype=np.float64)
    fixed_points = np.zeros((n_delta, n_acq, 3), dtype=np.float64)
    individual_complex = np.zeros((n_delta, n_acq), dtype=np.complex128)

    physics = CorePhysicsConfig(
        t1_s=config.physics.t1_s,
        t2_s=config.physics.t2_s,
        m0=config.physics.m0,
    )

    for delta_index, delta_f in enumerate(delta_f_hz):
        delta_omega_rad_s = float(2.0 * np.pi * delta_f)
        for acquisition_index, compiled in enumerate(compiled_sequences):
            phi3, c3, f_list, g_list = compose_affine_sequence(
                segment_dt_s=compiled.event_dt_s,
                segment_ux=compiled.event_ux,
                segment_uy=compiled.event_uy,
                delta_omega_rad_s=delta_omega_rad_s,
                physics=physics,
            )
            fixed_point = solve_fixed_point(phi3, c3)
            canonical_orbit = reconstruct_orbit(fixed_point, f_list, g_list, boundary_time_s)
            readout_profile = compute_readout_profile(
                fixed_point,
                per_acquisition_xy[acquisition_index],
                delta_omega_rad_s,
                config,
            )
            reference_m = _compute_reference_trajectory(
                boundary_time_s=boundary_time_s,
                compiled=compiled,
                delta_omega_rad_s=delta_omega_rad_s,
                physics=physics,
                config=config,
                t_eval=rk_time_s,
                reference_grid_spec=reference_grid_spec,
            )
            _, dense_orbit = integrate_reference_trajectory_with_affine_grid(
                boundary_time_s=boundary_time_s,
                segment_ux=compiled.event_ux,
                segment_uy=compiled.event_uy,
                delta_omega_rad_s=delta_omega_rad_s,
                physics=physics,
                grid_spec=steady_state_grid_spec,
                initial_state=fixed_point,
            )

            rk_m[delta_index, acquisition_index] = reference_m
            canonical_reference_m[delta_index, acquisition_index] = reference_m[
                reference_boundary_indices
            ]
            canonical_orbit_m[delta_index, acquisition_index] = canonical_orbit
            orbit_m[delta_index, acquisition_index] = dense_orbit
            fixed_points[delta_index, acquisition_index] = fixed_point
            individual_complex[delta_index, acquisition_index] = readout_profile

    individual_abs = np.abs(individual_complex)
    sos_abs = np.sqrt(PROFILE_EPSILON**2 + np.sum(individual_abs**2, axis=1))

    return SimulationResult(
        sequence_family=SequenceFamily.BSSFP,
        run_label=run_label,
        case_name=config.meta.case_name,
        description=config.meta.description,
        metadata={
            "runner": "bssfp_family_runner",
            "comparison_ready": "true",
        },
        family_metadata={
            "waveform_kind": config.sequence.waveform_kind,
            "readout_fraction_of_free": config.sequence.readout_fraction_of_free,
            "phase_cycles_deg": config.phase_cycles.values_deg.tolist(),
        },
        axes={
            "delta_f_hz": np.asarray(delta_f_hz, dtype=np.float64),
            "rk_time_s": np.asarray(rk_time_s, dtype=np.float64),
            "reference_time_s": np.asarray(canonical_reference_time_s, dtype=np.float64),
            "orbit_time_s": np.asarray(orbit_time_s, dtype=np.float64),
            "steady_state_time_s": np.asarray(canonical_orbit_time_s, dtype=np.float64),
        },
        trajectories={
            "rk_m": np.asarray(rk_m, dtype=np.float64),
            "reference_m": np.asarray(canonical_reference_m, dtype=np.float64),
            "orbit_m": np.asarray(orbit_m, dtype=np.float64),
            "steady_state_orbit_m": np.asarray(canonical_orbit_m, dtype=np.float64),
        },
        observables={
            "base_rf_xy": np.asarray(base_rf_xy, dtype=np.float64),
            "per_acquisition_xy": np.asarray(per_acquisition_xy, dtype=np.float64),
            "fixed_points": np.asarray(fixed_points, dtype=np.float64),
            "individual_complex": np.asarray(individual_complex, dtype=np.complex128),
            "individual_abs": np.asarray(individual_abs, dtype=np.float64),
            "sos_abs": np.asarray(sos_abs, dtype=np.float64),
        },
        scalars={
            "n_acquisitions": n_acq,
            "n_delta_f": int(delta_f_hz.shape[0]),
            "n_rk_time_samples": int(rk_time_s.shape[0]),
            "n_reference_time_samples": int(canonical_reference_time_s.shape[0]),
            "n_orbit_time_samples": int(orbit_time_s.shape[0]),
            "n_steady_state_time_samples": int(canonical_orbit_time_s.shape[0]),
            "individual_profile_abs_min": float(np.min(individual_abs)),
            "individual_profile_abs_max": float(np.max(individual_abs)),
            "sos_profile_abs_min": float(np.min(sos_abs)),
            "sos_profile_abs_max": float(np.max(sos_abs)),
        },
    )


def _build_superperiod_timing(config: RunConfig) -> tuple[FloatArray, FloatArray]:
    dt_rf = config.sequence.rf_duration_s / config.sequence.n_rf
    free_duration_s = config.sequence.free_duration_s
    segment_dt_s = np.concatenate(
        [
            np.full(config.sequence.n_rf, dt_rf, dtype=np.float64),
            np.array([free_duration_s], dtype=np.float64),
            np.full(config.sequence.n_rf, dt_rf, dtype=np.float64),
            np.array([free_duration_s], dtype=np.float64),
        ]
    )
    boundary_time_s = np.concatenate(
        [np.array([0.0], dtype=np.float64), np.cumsum(segment_dt_s, dtype=np.float64)]
    )
    return segment_dt_s, boundary_time_s


def _build_segment_controls(actual_rf_xy_for_one_acq: FloatArray) -> tuple[FloatArray, FloatArray]:
    segment_ux = np.concatenate(
        [
            actual_rf_xy_for_one_acq[0, :, 0],
            np.array([0.0], dtype=np.float64),
            actual_rf_xy_for_one_acq[1, :, 0],
            np.array([0.0], dtype=np.float64),
        ]
    )
    segment_uy = np.concatenate(
        [
            actual_rf_xy_for_one_acq[0, :, 1],
            np.array([0.0], dtype=np.float64),
            actual_rf_xy_for_one_acq[1, :, 1],
            np.array([0.0], dtype=np.float64),
        ]
    )
    return np.asarray(segment_ux, dtype=np.float64), np.asarray(segment_uy, dtype=np.float64)


def _build_superperiod_rk_grid(config: RunConfig, segment_dt_s: FloatArray) -> FloatArray:
    samples = [0.0]
    current_time_s = 0.0
    for dt_s in segment_dt_s:
        if config.integration.save_every_time_step:
            n_substeps = max(1, int(np.ceil(float(dt_s) / config.integration.rk_max_step_s)))
        else:
            n_substeps = 1
        local_points = current_time_s + np.linspace(
            float(dt_s) / n_substeps,
            float(dt_s),
            n_substeps,
            dtype=np.float64,
        )
        samples.extend(local_points.tolist())
        current_time_s += float(dt_s)
    return np.asarray(samples, dtype=np.float64)


def _tile_superperiod_time_grid(superperiod_time_s: FloatArray, n_superperiods: int) -> FloatArray:
    period_s = float(superperiod_time_s[-1])
    tiled = [np.asarray(superperiod_time_s, dtype=np.float64)]
    for superperiod_index in range(1, n_superperiods):
        tiled.append(
            np.asarray(superperiod_time_s[1:] + superperiod_index * period_s, dtype=np.float64)
        )
    return np.concatenate(tiled)


def _build_repeated_boundary_indices(
    superperiod_time_s: FloatArray,
    boundary_time_s: FloatArray,
    n_superperiods: int,
) -> npt.NDArray[np.int64]:
    per_superperiod_indices = np.asarray(
        [
            int(np.argmin(np.abs(superperiod_time_s - boundary_time)))
            for boundary_time in boundary_time_s
        ],
        dtype=np.int64,
    )
    repeated_indices = [per_superperiod_indices]
    per_superperiod_sample_count = superperiod_time_s.shape[0] - 1
    for superperiod_index in range(1, n_superperiods):
        repeated_indices.append(
            per_superperiod_indices[1:] + superperiod_index * per_superperiod_sample_count
        )
    return np.concatenate(repeated_indices)


def _compute_reference_trajectory(
    *,
    boundary_time_s: FloatArray,
    compiled: CompiledSequence,
    delta_omega_rad_s: float,
    physics: CorePhysicsConfig,
    config: RunConfig,
    t_eval: FloatArray,
    reference_grid_spec: AffineReferenceGridSpec,
) -> FloatArray:
    initial_state = np.asarray([0.0, 0.0, config.physics.m0], dtype=np.float64)
    if config.integration.rk_method == "PROPAGATOR":
        _, reference_m = integrate_reference_trajectory_with_affine_grid(
            boundary_time_s=boundary_time_s,
            segment_ux=compiled.event_ux,
            segment_uy=compiled.event_uy,
            delta_omega_rad_s=delta_omega_rad_s,
            physics=physics,
            grid_spec=reference_grid_spec,
            initial_state=initial_state,
        )
        return reference_m

    _, reference_m = integrate_reference_trajectory_with_grid(
        boundary_time_s=boundary_time_s,
        segment_ux=compiled.event_ux,
        segment_uy=compiled.event_uy,
        delta_omega_rad_s=delta_omega_rad_s,
        total_duration_s=float(t_eval[-1]),
        physics=physics,
        t_eval=t_eval,
        method=cast(SolveIvpMethod, config.integration.rk_method),
        rtol=config.integration.rk_rtol,
        atol=config.integration.rk_atol,
        max_step_s=config.integration.rk_max_step_s,
        initial_state=initial_state,
    )
    return reference_m

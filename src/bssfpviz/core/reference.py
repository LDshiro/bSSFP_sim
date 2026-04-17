"""RK45 reference integration for the Chapter 3 Bloch model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt
from scipy.integrate import solve_ivp

from bssfpviz.core.bloch import bloch_matrix, bloch_offset_vector
from bssfpviz.core.propagators import segment_affine_propagator
from bssfpviz.core.segments import build_superperiod_segments
from bssfpviz.models.config import PhysicsConfig, SimulationConfig

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]
SolveIvpMethod = Literal["RK23", "RK45", "DOP853", "Radau", "BDF", "LSODA"]
_GRID_TOLERANCE_S = 1.0e-12


@dataclass(frozen=True, slots=True)
class AffineReferenceGridSpec:
    """Validated explicit grid layout for the fast affine reference integrator."""

    t_eval: FloatArray
    substeps_per_segment: IntArray
    n_superperiods: int


def integrate_reference_trajectory(
    actual_rf_xy_for_one_acq: FloatArray,
    delta_omega_rad_s: float,
    config: SimulationConfig,
    physics: PhysicsConfig,
) -> tuple[FloatArray, FloatArray]:
    """Integrate the repeated 2TR trajectory with RK45 on the boundary grid."""
    segment_sequence = build_superperiod_segments(
        actual_rf_xy=actual_rf_xy_for_one_acq,
        delta_omega_rad_s=delta_omega_rad_s,
        config=config,
    )
    t_eval = _make_reference_eval_grid(segment_sequence.boundary_time_s, config.sequence.n_cycles)
    return integrate_reference_trajectory_with_grid(
        boundary_time_s=segment_sequence.boundary_time_s,
        segment_ux=segment_sequence.segment_ux,
        segment_uy=segment_sequence.segment_uy,
        delta_omega_rad_s=delta_omega_rad_s,
        total_duration_s=config.sequence.n_cycles * config.superperiod_duration_s,
        physics=physics,
        t_eval=t_eval,
        method="RK45",
        rtol=1e-8,
        atol=1e-10,
        max_step_s=min(
            config.sampling.rk_dt_s, config.sequence.rf_duration_s / config.sequence.n_rf_samples
        ),
        initial_state=np.asarray([0.0, 0.0, physics.m0], dtype=np.float64),
    )


def integrate_reference_trajectory_with_grid(
    *,
    boundary_time_s: FloatArray,
    segment_ux: FloatArray,
    segment_uy: FloatArray,
    delta_omega_rad_s: float,
    total_duration_s: float,
    physics: PhysicsConfig,
    t_eval: FloatArray,
    method: SolveIvpMethod = "RK45",
    rtol: float = 1.0e-8,
    atol: float = 1.0e-10,
    max_step_s: float | None = None,
    initial_state: FloatArray | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Integrate one repeated 2TR control sequence on an explicit shared time grid."""
    boundary_time_s = np.asarray(boundary_time_s, dtype=np.float64)
    segment_ux = np.asarray(segment_ux, dtype=np.float64)
    segment_uy = np.asarray(segment_uy, dtype=np.float64)
    t_eval = np.asarray(t_eval, dtype=np.float64)

    if boundary_time_s.ndim != 1 or segment_ux.ndim != 1 or segment_uy.ndim != 1:
        msg = "boundary_time_s, segment_ux, and segment_uy must be 1D arrays."
        raise ValueError(msg)
    if boundary_time_s.shape != (segment_ux.shape[0] + 1,) or segment_ux.shape != segment_uy.shape:
        msg = "boundary_time_s, segment_ux, and segment_uy must have consistent shapes."
        raise ValueError(msg)
    if t_eval.ndim != 1 or t_eval.shape[0] == 0:
        msg = "t_eval must be a non-empty 1D array."
        raise ValueError(msg)
    if not np.all(np.diff(t_eval) > 0.0):
        msg = "t_eval must be strictly increasing."
        raise ValueError(msg)
    if t_eval[0] < 0.0 or t_eval[-1] > total_duration_s + 1.0e-15:
        msg = "t_eval must lie within the requested integration interval."
        raise ValueError(msg)

    superperiod_duration_s = float(boundary_time_s[-1])
    initial_magnetization = (
        np.asarray([0.0, 0.0, physics.m0], dtype=np.float64)
        if initial_state is None
        else np.asarray(initial_state, dtype=np.float64)
    )

    def rhs(t_s: float, magnetization: FloatArray) -> FloatArray:
        t_mod_s = t_s % superperiod_duration_s
        segment_index = int(np.searchsorted(boundary_time_s, t_mod_s, side="right") - 1)
        segment_index = min(max(segment_index, 0), segment_ux.shape[0] - 1)
        generator = bloch_matrix(
            ux=float(segment_ux[segment_index]),
            uy=float(segment_uy[segment_index]),
            delta_omega_rad_s=delta_omega_rad_s,
            physics=physics,
        )
        offset = bloch_offset_vector(physics)
        return generator @ magnetization + offset

    if max_step_s is None:
        solution = solve_ivp(
            fun=rhs,
            t_span=(0.0, total_duration_s),
            y0=initial_magnetization,
            method=method,
            t_eval=t_eval,
            rtol=rtol,
            atol=atol,
        )
    else:
        solution = solve_ivp(
            fun=rhs,
            t_span=(0.0, total_duration_s),
            y0=initial_magnetization,
            method=method,
            t_eval=t_eval,
            rtol=rtol,
            atol=atol,
            max_step=max_step_s,
        )
    if not solution.success:
        msg = f"RK integration failed: {solution.message}"
        raise RuntimeError(msg)
    return np.asarray(solution.t, dtype=np.float64), np.asarray(solution.y.T, dtype=np.float64)


def build_affine_reference_grid_spec(
    *,
    boundary_time_s: FloatArray,
    total_duration_s: float,
    t_eval: FloatArray,
) -> AffineReferenceGridSpec:
    """Validate and encode a repeated segment-wise explicit grid for fast stepping."""
    boundary_time_s = np.asarray(boundary_time_s, dtype=np.float64)
    t_eval = np.asarray(t_eval, dtype=np.float64)

    if boundary_time_s.ndim != 1 or boundary_time_s.shape[0] < 2:
        msg = "boundary_time_s must be a 1D array with at least two entries."
        raise ValueError(msg)
    if t_eval.ndim != 1 or t_eval.shape[0] == 0:
        msg = "t_eval must be a non-empty 1D array."
        raise ValueError(msg)
    if not np.all(np.diff(boundary_time_s) > 0.0):
        msg = "boundary_time_s must be strictly increasing."
        raise ValueError(msg)
    if not np.all(np.diff(t_eval) > 0.0):
        msg = "t_eval must be strictly increasing."
        raise ValueError(msg)
    if not np.isclose(t_eval[0], 0.0, atol=_GRID_TOLERANCE_S, rtol=0.0):
        msg = "t_eval must start at 0 for the fast affine integrator."
        raise ValueError(msg)
    if t_eval[-1] > total_duration_s + _GRID_TOLERANCE_S:
        msg = "t_eval must lie within the requested integration interval."
        raise ValueError(msg)

    superperiod_duration_s = float(boundary_time_s[-1])
    if superperiod_duration_s <= 0.0:
        msg = "boundary_time_s must describe a positive-duration superperiod."
        raise ValueError(msg)

    n_superperiods = _infer_superperiod_count(
        total_duration_s=total_duration_s,
        superperiod_duration_s=superperiod_duration_s,
    )
    superperiod_t_eval = t_eval[t_eval <= superperiod_duration_s + _GRID_TOLERANCE_S]
    substeps_per_segment = _infer_substeps_per_segment(boundary_time_s, superperiod_t_eval)
    expected_t_eval = _tile_segment_subdivision_grid(
        boundary_time_s=boundary_time_s,
        substeps_per_segment=substeps_per_segment,
        n_superperiods=n_superperiods,
    )
    if expected_t_eval.shape != t_eval.shape or not np.allclose(
        expected_t_eval,
        t_eval,
        atol=_GRID_TOLERANCE_S,
        rtol=0.0,
    ):
        msg = (
            "t_eval must be built from repeated equal subdivisions of each "
            "piecewise-constant segment."
        )
        raise ValueError(msg)

    return AffineReferenceGridSpec(
        t_eval=np.asarray(t_eval, dtype=np.float64),
        substeps_per_segment=np.asarray(substeps_per_segment, dtype=np.int64),
        n_superperiods=n_superperiods,
    )


def integrate_reference_trajectory_with_affine_grid(
    *,
    boundary_time_s: FloatArray,
    segment_ux: FloatArray,
    segment_uy: FloatArray,
    delta_omega_rad_s: float,
    physics: PhysicsConfig,
    grid_spec: AffineReferenceGridSpec,
    initial_state: FloatArray | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Integrate on an explicit repeated grid using exact affine segment substeps."""
    boundary_time_s = np.asarray(boundary_time_s, dtype=np.float64)
    segment_ux = np.asarray(segment_ux, dtype=np.float64)
    segment_uy = np.asarray(segment_uy, dtype=np.float64)

    if boundary_time_s.shape != (segment_ux.shape[0] + 1,) or segment_ux.shape != segment_uy.shape:
        msg = "boundary_time_s, segment_ux, and segment_uy must have consistent shapes."
        raise ValueError(msg)
    if grid_spec.substeps_per_segment.shape != segment_ux.shape:
        msg = "grid_spec.substeps_per_segment must align with the segment controls."
        raise ValueError(msg)

    initial_magnetization = (
        np.asarray([0.0, 0.0, physics.m0], dtype=np.float64)
        if initial_state is None
        else np.asarray(initial_state, dtype=np.float64)
    )
    if initial_magnetization.shape != (3,):
        msg = "initial_state must be a 3-vector."
        raise ValueError(msg)

    segment_dt_s = np.diff(boundary_time_s)
    step_count = 1 + grid_spec.n_superperiods * int(np.sum(grid_spec.substeps_per_segment))
    if step_count != grid_spec.t_eval.shape[0]:
        msg = "grid_spec does not match the requested t_eval length."
        raise ValueError(msg)

    segment_propagators: list[tuple[FloatArray, FloatArray, int]] = []
    for segment_index, n_substeps in enumerate(grid_spec.substeps_per_segment):
        substep_dt_s = float(segment_dt_s[segment_index]) / float(n_substeps)
        phi3, c3, _ = segment_affine_propagator(
            ux=float(segment_ux[segment_index]),
            uy=float(segment_uy[segment_index]),
            delta_omega_rad_s=delta_omega_rad_s,
            dt_s=substep_dt_s,
            physics=physics,
        )
        segment_propagators.append((phi3, c3, int(n_substeps)))

    magnetization = np.empty((grid_spec.t_eval.shape[0], 3), dtype=np.float64)
    current_state = np.asarray(initial_magnetization, dtype=np.float64)
    magnetization[0] = current_state
    output_index = 1

    for _ in range(grid_spec.n_superperiods):
        for phi3, c3, n_substeps in segment_propagators:
            for _ in range(n_substeps):
                current_state = phi3 @ current_state + c3
                magnetization[output_index] = current_state
                output_index += 1

    return np.asarray(grid_spec.t_eval, dtype=np.float64), magnetization


def _make_reference_eval_grid(boundary_time_s: FloatArray, n_cycles: int) -> FloatArray:
    period_s = float(boundary_time_s[-1])
    grids = [np.asarray(boundary_time_s, dtype=np.float64)]
    for cycle_index in range(1, n_cycles):
        grids.append(np.asarray(boundary_time_s[1:] + cycle_index * period_s, dtype=np.float64))
    return np.concatenate(grids)


def _infer_superperiod_count(*, total_duration_s: float, superperiod_duration_s: float) -> int:
    n_superperiods_float = float(total_duration_s) / float(superperiod_duration_s)
    n_superperiods = int(round(n_superperiods_float))
    if n_superperiods <= 0 or not np.isclose(
        total_duration_s,
        n_superperiods * superperiod_duration_s,
        atol=_GRID_TOLERANCE_S,
        rtol=0.0,
    ):
        msg = "total_duration_s must be an integer multiple of the superperiod duration."
        raise ValueError(msg)
    return n_superperiods


def _infer_substeps_per_segment(
    boundary_time_s: FloatArray, superperiod_t_eval: FloatArray
) -> IntArray:
    substeps_per_segment = np.zeros(boundary_time_s.shape[0] - 1, dtype=np.int64)
    for segment_index in range(substeps_per_segment.shape[0]):
        segment_start_s = float(boundary_time_s[segment_index])
        segment_end_s = float(boundary_time_s[segment_index + 1])
        segment_mask = (superperiod_t_eval > segment_start_s + _GRID_TOLERANCE_S) & (
            superperiod_t_eval <= segment_end_s + _GRID_TOLERANCE_S
        )
        segment_points = np.asarray(superperiod_t_eval[segment_mask], dtype=np.float64)
        if segment_points.shape[0] == 0:
            msg = "Each segment must contain at least one explicit sample in t_eval."
            raise ValueError(msg)
        expected_segment_points = segment_start_s + np.linspace(
            (segment_end_s - segment_start_s) / segment_points.shape[0],
            segment_end_s - segment_start_s,
            segment_points.shape[0],
            dtype=np.float64,
        )
        if not np.allclose(
            segment_points,
            expected_segment_points,
            atol=_GRID_TOLERANCE_S,
            rtol=0.0,
        ):
            msg = "Each segment in t_eval must be sampled on an equal subdivision grid."
            raise ValueError(msg)
        substeps_per_segment[segment_index] = int(segment_points.shape[0])
    return substeps_per_segment


def _tile_segment_subdivision_grid(
    *,
    boundary_time_s: FloatArray,
    substeps_per_segment: IntArray,
    n_superperiods: int,
) -> FloatArray:
    superperiod_samples = [0.0]
    current_time_s = 0.0
    for segment_index, n_substeps in enumerate(substeps_per_segment):
        segment_dt_s = float(boundary_time_s[segment_index + 1] - boundary_time_s[segment_index])
        segment_points = current_time_s + np.linspace(
            segment_dt_s / float(n_substeps),
            segment_dt_s,
            int(n_substeps),
            dtype=np.float64,
        )
        superperiod_samples.extend(segment_points.tolist())
        current_time_s += segment_dt_s

    superperiod_time_s = np.asarray(superperiod_samples, dtype=np.float64)
    tiled = [superperiod_time_s]
    period_s = float(superperiod_time_s[-1])
    for superperiod_index in range(1, n_superperiods):
        tiled.append(superperiod_time_s[1:] + float(superperiod_index) * period_s)
    return np.concatenate(tiled)

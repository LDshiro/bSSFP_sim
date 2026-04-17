"""Chapter 4 compute runner and HDF5 export."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import h5py
import numpy as np
import numpy.typing as npt

from bssfpviz import __version__
from bssfpviz.core.propagators import compose_affine_sequence, segment_affine_propagator
from bssfpviz.core.reference import (
    build_affine_reference_grid_spec,
    integrate_reference_trajectory_with_affine_grid,
)
from bssfpviz.core.segments import materialize_actual_waveforms
from bssfpviz.core.steady_state import reconstruct_orbit, solve_fixed_point
from bssfpviz.models.config import SCHEMA_VERSION
from bssfpviz.models.config import PhysicsConfig as CorePhysicsConfig
from bssfpviz.models.run_config import RunConfig

ComplexArray = npt.NDArray[np.complex128]
FloatArray = npt.NDArray[np.float64]

PROFILE_EPSILON = 1.0e-12
DEFAULT_GAMMA_RAD_PER_S_PER_T = CorePhysicsConfig().gamma_rad_per_s_per_t


@dataclass(slots=True)
class ComputeSummary:
    """High-level summary of one compute run."""

    case_name: str
    n_acquisitions: int
    n_delta_f: int
    n_time_samples: int
    output_path: Path
    elapsed_seconds: float
    min_profile_individual: float
    max_profile_individual: float
    min_profile_sos: float
    max_profile_sos: float

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        data = asdict(self)
        data["output_path"] = str(self.output_path)
        return data


@dataclass(slots=True)
class _ComputedArrays:
    """Intermediate arrays for HDF5 serialization."""

    delta_f_hz: FloatArray
    base_rf_xy: FloatArray
    per_acquisition_xy: FloatArray
    rk_time_s: FloatArray
    rk_m: FloatArray
    canonical_reference_time_s: FloatArray
    canonical_reference_m: FloatArray
    canonical_orbit_time_s: FloatArray
    canonical_orbit_m: FloatArray
    orbit_time_s: FloatArray
    orbit_m: FloatArray
    fixed_points: FloatArray
    individual_complex: ComplexArray
    individual_abs: FloatArray
    sos_abs: FloatArray


def run_compute(config: RunConfig, output_path: Path) -> ComputeSummary:
    """Run the Chapter 4 compute workflow and save its HDF5 output."""
    start_time = perf_counter()
    arrays = _compute_arrays(config)
    _write_compute_hdf5(output_path, config, arrays)

    elapsed_seconds = perf_counter() - start_time
    return ComputeSummary(
        case_name=config.meta.case_name,
        n_acquisitions=config.n_acquisitions,
        n_delta_f=int(arrays.delta_f_hz.shape[0]),
        n_time_samples=int(arrays.rk_time_s.shape[0]),
        output_path=output_path,
        elapsed_seconds=elapsed_seconds,
        min_profile_individual=float(np.min(arrays.individual_abs)),
        max_profile_individual=float(np.max(arrays.individual_abs)),
        min_profile_sos=float(np.min(arrays.sos_abs)),
        max_profile_sos=float(np.max(arrays.sos_abs)),
    )


def _compute_arrays(config: RunConfig) -> _ComputedArrays:
    delta_f_hz = config.sweep.build_delta_f_hz()
    phase_cycles_rad = config.phase_cycles.build_values_rad()
    base_rf_xy = _make_base_waveform(config)
    per_acquisition_xy = materialize_actual_waveforms(base_rf_xy, phase_cycles_rad)

    segment_dt_s, boundary_time_s = _build_superperiod_timing(config)
    canonical_reference_time_s = _tile_superperiod_time_grid(
        np.asarray(boundary_time_s, dtype=np.float64),
        config.integration.rk_superperiods,
    )
    dense_superperiod_time_s = _build_superperiod_rk_grid(config, segment_dt_s)
    rk_time_s = _tile_superperiod_time_grid(
        dense_superperiod_time_s, config.integration.rk_superperiods
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

    core_physics = CorePhysicsConfig(
        t1_s=config.physics.t1_s,
        t2_s=config.physics.t2_s,
        m0=config.physics.m0,
    )
    per_acquisition_controls = [
        _build_segment_controls(per_acquisition_xy[acquisition_index])
        for acquisition_index in range(n_acq)
    ]

    for delta_index, delta_f in enumerate(delta_f_hz):
        delta_omega_rad_s = float(2.0 * np.pi * delta_f)
        for acquisition_index in range(n_acq):
            segment_ux, segment_uy = per_acquisition_controls[acquisition_index]
            phi3, c3, f_list, g_list = compose_affine_sequence(
                segment_dt_s=segment_dt_s,
                segment_ux=segment_ux,
                segment_uy=segment_uy,
                delta_omega_rad_s=delta_omega_rad_s,
                physics=core_physics,
            )
            fixed_point = solve_fixed_point(phi3, c3)
            canonical_orbit = reconstruct_orbit(fixed_point, f_list, g_list, boundary_time_s)
            readout_profile = _compute_readout_profile(
                fixed_point,
                segment_ux,
                segment_uy,
                delta_omega_rad_s,
                core_physics,
                config,
            )
            _, reference_m = integrate_reference_trajectory_with_affine_grid(
                boundary_time_s=boundary_time_s,
                segment_ux=segment_ux,
                segment_uy=segment_uy,
                delta_omega_rad_s=delta_omega_rad_s,
                physics=core_physics,
                grid_spec=reference_grid_spec,
                initial_state=np.asarray([0.0, 0.0, config.physics.m0], dtype=np.float64),
            )
            _, dense_orbit = integrate_reference_trajectory_with_affine_grid(
                boundary_time_s=boundary_time_s,
                segment_ux=segment_ux,
                segment_uy=segment_uy,
                delta_omega_rad_s=delta_omega_rad_s,
                physics=core_physics,
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

    return _ComputedArrays(
        delta_f_hz=np.asarray(delta_f_hz, dtype=np.float64),
        base_rf_xy=np.asarray(base_rf_xy, dtype=np.float64),
        per_acquisition_xy=np.asarray(per_acquisition_xy, dtype=np.float64),
        rk_time_s=np.asarray(rk_time_s, dtype=np.float64),
        rk_m=np.asarray(rk_m, dtype=np.float64),
        canonical_reference_time_s=np.asarray(canonical_reference_time_s, dtype=np.float64),
        canonical_reference_m=np.asarray(canonical_reference_m, dtype=np.float64),
        canonical_orbit_time_s=np.asarray(canonical_orbit_time_s, dtype=np.float64),
        canonical_orbit_m=np.asarray(canonical_orbit_m, dtype=np.float64),
        orbit_time_s=np.asarray(orbit_time_s, dtype=np.float64),
        orbit_m=np.asarray(orbit_m, dtype=np.float64),
        fixed_points=np.asarray(fixed_points, dtype=np.float64),
        individual_complex=np.asarray(individual_complex, dtype=np.complex128),
        individual_abs=np.asarray(individual_abs, dtype=np.float64),
        sos_abs=np.asarray(sos_abs, dtype=np.float64),
    )


def _make_base_waveform(config: RunConfig) -> FloatArray:
    n_rf = config.sequence.n_rf
    dt_rf = config.sequence.rf_duration_s / n_rf

    if config.sequence.waveform_kind == "hann":
        if n_rf == 1:
            envelope = np.ones(1, dtype=np.float64)
        else:
            samples = np.arange(n_rf, dtype=np.float64)
            envelope = 0.5 * (1.0 - np.cos((2.0 * np.pi * samples) / (n_rf - 1)))
    else:
        envelope = np.ones(n_rf, dtype=np.float64)

    scale = config.sequence.alpha_rad / (np.sum(envelope) * dt_rf)
    base_rf_xy = np.zeros((n_rf, 2), dtype=np.float64)
    base_rf_xy[:, 0] = scale * envelope
    return base_rf_xy


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
    superperiod_time_s: FloatArray, boundary_time_s: FloatArray, n_superperiods: int
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


def _compute_readout_profile(
    fixed_point: FloatArray,
    segment_ux: FloatArray,
    segment_uy: FloatArray,
    delta_omega_rad_s: float,
    physics: CorePhysicsConfig,
    config: RunConfig,
) -> complex:
    pulse_dt_s = np.full(
        config.sequence.n_rf,
        config.sequence.rf_duration_s / config.sequence.n_rf,
        dtype=np.float64,
    )
    pulse_phi, pulse_c, _, _ = compose_affine_sequence(
        segment_dt_s=pulse_dt_s,
        segment_ux=segment_ux[: config.sequence.n_rf],
        segment_uy=segment_uy[: config.sequence.n_rf],
        delta_omega_rad_s=delta_omega_rad_s,
        physics=physics,
    )
    after_pulse = pulse_phi @ fixed_point + pulse_c

    if np.isclose(config.sequence.readout_fraction_of_free, 0.0):
        magnetization_ro = after_pulse
    else:
        free_map, free_offset, _ = segment_affine_propagator(
            ux=0.0,
            uy=0.0,
            delta_omega_rad_s=delta_omega_rad_s,
            dt_s=config.sequence.readout_fraction_of_free * config.sequence.free_duration_s,
            physics=physics,
        )
        magnetization_ro = free_map @ after_pulse + free_offset
    return complex(magnetization_ro[0], magnetization_ro[1])


def _write_compute_hdf5(output_path: Path, config: RunConfig, arrays: _ComputedArrays) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_canonical_compat = np.isclose(config.sequence.readout_fraction_of_free, 0.5)

    with h5py.File(output_path, "w") as handle:
        _write_root_attrs(handle)
        _write_string_dataset(handle, "/meta/run_name", config.meta.case_name)
        _write_string_dataset(handle, "/meta/user_notes", config.meta.description)
        _write_string_dataset(handle, "/meta/case_name", config.meta.case_name)
        _write_string_dataset(handle, "/meta/description", config.meta.description)

        _write_scalar_dataset(handle, "/config/physics/T1_s", config.physics.t1_s)
        _write_scalar_dataset(handle, "/config/physics/T2_s", config.physics.t2_s)
        _write_scalar_dataset(handle, "/config/physics/M0", config.physics.m0)
        if write_canonical_compat:
            _write_scalar_dataset(
                handle,
                "/config/physics/gamma_rad_per_s_per_T",
                DEFAULT_GAMMA_RAD_PER_S_PER_T,
            )

        _write_scalar_dataset(handle, "/config/sequence/TR_s", config.sequence.tr_s)
        _write_scalar_dataset(
            handle, "/config/sequence/rf_duration_s", config.sequence.rf_duration_s
        )
        _write_scalar_dataset(handle, "/config/sequence/n_rf", config.sequence.n_rf)
        _write_scalar_dataset(handle, "/config/sequence/alpha_deg", config.sequence.alpha_deg)
        _write_scalar_dataset(
            handle,
            "/config/sequence/readout_fraction_of_free",
            config.sequence.readout_fraction_of_free,
        )
        if write_canonical_compat:
            _write_scalar_dataset(handle, "/config/sequence/TE_s", config.sequence.readout_time_s)
            _write_scalar_dataset(
                handle, "/config/sequence/free_duration_s", config.sequence.free_duration_s
            )
            _write_scalar_dataset(handle, "/config/sequence/n_rf_samples", config.sequence.n_rf)
            _write_scalar_dataset(
                handle, "/config/sequence/flip_angle_rad", config.sequence.alpha_rad
            )
            _write_scalar_dataset(
                handle, "/config/sequence/n_cycles", config.integration.rk_superperiods
            )
            _write_array_dataset(
                handle,
                "/config/sequence/phase_schedule_rad",
                config.phase_cycles.build_values_rad(),
            )

        _write_array_dataset(
            handle, "/config/phase_cycles/values_deg", config.phase_cycles.values_deg
        )

        _write_array_dataset(handle, "/sweep/delta_f_hz", arrays.delta_f_hz)
        if write_canonical_compat:
            _write_array_dataset(handle, "/config/sampling/delta_f_hz", arrays.delta_f_hz)
            _write_scalar_dataset(
                handle, "/config/sampling/rk_dt_s", config.integration.rk_max_step_s
            )
            _write_scalar_dataset(
                handle,
                "/config/sampling/steady_state_dt_s",
                config.sequence.rf_duration_s / config.sequence.n_rf,
            )
            _write_scalar_dataset(
                handle,
                "/config/sampling/n_reference_steps",
                arrays.canonical_reference_time_s.shape[0],
            )
            _write_scalar_dataset(
                handle,
                "/config/sampling/n_steady_state_steps",
                arrays.canonical_orbit_time_s.shape[0],
            )

        _write_array_dataset(handle, "/waveforms/base_xy", arrays.base_rf_xy)
        _write_array_dataset(handle, "/waveforms/per_acquisition_xy", arrays.per_acquisition_xy)
        if write_canonical_compat:
            _write_array_dataset(handle, "/waveforms/rf_xy", arrays.base_rf_xy)

        if config.output.save_rk_trajectories:
            _write_array_dataset(handle, "/rk/time_s", arrays.rk_time_s)
            _write_array_dataset(handle, "/rk/M", arrays.rk_m)
            if write_canonical_compat:
                _write_array_dataset(
                    handle, "/time/reference_time_s", arrays.canonical_reference_time_s
                )
                _write_array_dataset(
                    handle,
                    "/reference/M_xyz",
                    np.transpose(arrays.canonical_reference_m, (1, 0, 2, 3)),
                )

        if config.output.save_steady_state_orbit:
            _write_array_dataset(handle, "/steady_state/orbit_time_s", arrays.orbit_time_s)
            _write_array_dataset(handle, "/steady_state/orbit_M", arrays.orbit_m)
            if write_canonical_compat:
                _write_array_dataset(
                    handle, "/time/steady_state_time_s", arrays.canonical_orbit_time_s
                )
                _write_array_dataset(
                    handle,
                    "/steady_state/orbit_xyz",
                    np.transpose(arrays.canonical_orbit_m, (1, 0, 2, 3)),
                )

        if config.output.save_fixed_points:
            _write_array_dataset(handle, "/steady_state/fixed_points", arrays.fixed_points)
            if write_canonical_compat:
                _write_array_dataset(
                    handle,
                    "/steady_state/fixed_point_xyz",
                    np.transpose(arrays.fixed_points, (1, 0, 2)),
                )

        if config.output.save_profiles:
            individual_complex_realimag = np.stack(
                [arrays.individual_complex.real, arrays.individual_complex.imag], axis=-1
            )
            _write_array_dataset(
                handle,
                "/profiles/individual_complex_realimag",
                individual_complex_realimag,
            )
            _write_array_dataset(handle, "/profiles/individual_abs", arrays.individual_abs)
            _write_array_dataset(handle, "/profiles/sos_abs", arrays.sos_abs)
            if write_canonical_compat:
                _write_array_dataset(
                    handle,
                    "/profiles/individual_complex",
                    np.asarray(arrays.individual_complex.T, dtype=np.complex128),
                )
                _write_array_dataset(handle, "/profiles/sos_magnitude", arrays.sos_abs)


def _write_root_attrs(handle: h5py.File) -> None:
    created_at_utc = datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    handle.attrs["schema_version"] = SCHEMA_VERSION
    handle.attrs["created_at_utc"] = created_at_utc
    handle.attrs["app_name"] = "bloch-ssfp-visualizer"
    handle.attrs["app_version"] = __version__
    handle.attrs["git_commit"] = "unknown"


def _write_scalar_dataset(handle: h5py.File, path: str, value: float | int) -> None:
    group_path, dataset_name = path.rsplit("/", maxsplit=1)
    group = handle.require_group(group_path)
    group.create_dataset(dataset_name, data=value)


def _write_array_dataset(handle: h5py.File, path: str, value: np.ndarray) -> None:
    group_path, dataset_name = path.rsplit("/", maxsplit=1)
    group = handle.require_group(group_path)
    group.create_dataset(dataset_name, data=value)


def _write_string_dataset(handle: h5py.File, path: str, value: str) -> None:
    group_path, dataset_name = path.rsplit("/", maxsplit=1)
    group = handle.require_group(group_path)
    group.create_dataset(dataset_name, data=value, dtype=h5py.string_dtype(encoding="utf-8"))

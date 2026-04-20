"""Legacy bSSFP HDF5 writer adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import h5py
import numpy as np

from bssfpviz import __version__
from bssfpviz.models.comparison import SimulationResult
from bssfpviz.models.config import SCHEMA_VERSION
from bssfpviz.models.config import PhysicsConfig as CorePhysicsConfig
from bssfpviz.models.run_config import RunConfig

DEFAULT_GAMMA_RAD_PER_S_PER_T = CorePhysicsConfig().gamma_rad_per_s_per_t


def save_legacy_bssfp_result(
    output_path: Path,
    config: RunConfig,
    result: SimulationResult,
) -> None:
    """Write a generic bSSFP SimulationResult using the legacy HDF5 layout."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_canonical_compat = np.isclose(config.sequence.readout_fraction_of_free, 0.5)

    delta_f_hz = _require_axis(result, "delta_f_hz")
    rk_time_s = _require_axis(result, "rk_time_s")
    canonical_reference_time_s = _require_axis(result, "reference_time_s")
    orbit_time_s = _require_axis(result, "orbit_time_s")
    canonical_orbit_time_s = _require_axis(result, "steady_state_time_s")

    base_rf_xy = _require_observable(result, "base_rf_xy")
    per_acquisition_xy = _require_observable(result, "per_acquisition_xy")
    rk_m = _require_trajectory(result, "rk_m")
    canonical_reference_m = _require_trajectory(result, "reference_m")
    orbit_m = _require_trajectory(result, "orbit_m")
    canonical_orbit_m = _require_trajectory(result, "steady_state_orbit_m")
    fixed_points = _require_observable(result, "fixed_points")
    individual_complex = np.asarray(
        _require_observable(result, "individual_complex"),
        dtype=np.complex128,
    )
    individual_abs = _require_observable(result, "individual_abs")
    sos_abs = _require_observable(result, "sos_abs")

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
            handle,
            "/config/sequence/rf_duration_s",
            config.sequence.rf_duration_s,
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
                handle,
                "/config/sequence/free_duration_s",
                config.sequence.free_duration_s,
            )
            _write_scalar_dataset(handle, "/config/sequence/n_rf_samples", config.sequence.n_rf)
            _write_scalar_dataset(
                handle,
                "/config/sequence/flip_angle_rad",
                config.sequence.alpha_rad,
            )
            _write_scalar_dataset(
                handle,
                "/config/sequence/n_cycles",
                config.integration.rk_superperiods,
            )
            _write_array_dataset(
                handle,
                "/config/sequence/phase_schedule_rad",
                config.phase_cycles.build_values_rad(),
            )

        _write_array_dataset(
            handle,
            "/config/phase_cycles/values_deg",
            config.phase_cycles.values_deg,
        )
        _write_array_dataset(handle, "/sweep/delta_f_hz", delta_f_hz)
        if write_canonical_compat:
            _write_array_dataset(handle, "/config/sampling/delta_f_hz", delta_f_hz)
            _write_scalar_dataset(
                handle,
                "/config/sampling/rk_dt_s",
                config.integration.rk_max_step_s,
            )
            _write_scalar_dataset(
                handle,
                "/config/sampling/steady_state_dt_s",
                config.sequence.rf_duration_s / config.sequence.n_rf,
            )
            _write_scalar_dataset(
                handle,
                "/config/sampling/n_reference_steps",
                canonical_reference_time_s.shape[0],
            )
            _write_scalar_dataset(
                handle,
                "/config/sampling/n_steady_state_steps",
                canonical_orbit_time_s.shape[0],
            )

        _write_array_dataset(handle, "/waveforms/base_xy", base_rf_xy)
        _write_array_dataset(handle, "/waveforms/per_acquisition_xy", per_acquisition_xy)
        if write_canonical_compat:
            _write_array_dataset(handle, "/waveforms/rf_xy", base_rf_xy)

        if config.output.save_rk_trajectories:
            _write_array_dataset(handle, "/rk/time_s", rk_time_s)
            _write_array_dataset(handle, "/rk/M", rk_m)
            if write_canonical_compat:
                _write_array_dataset(handle, "/time/reference_time_s", canonical_reference_time_s)
                _write_array_dataset(
                    handle,
                    "/reference/M_xyz",
                    np.transpose(canonical_reference_m, (1, 0, 2, 3)),
                )

        if config.output.save_steady_state_orbit:
            _write_array_dataset(handle, "/steady_state/orbit_time_s", orbit_time_s)
            _write_array_dataset(handle, "/steady_state/orbit_M", orbit_m)
            if write_canonical_compat:
                _write_array_dataset(handle, "/time/steady_state_time_s", canonical_orbit_time_s)
                _write_array_dataset(
                    handle,
                    "/steady_state/orbit_xyz",
                    np.transpose(canonical_orbit_m, (1, 0, 2, 3)),
                )

        if config.output.save_fixed_points:
            _write_array_dataset(handle, "/steady_state/fixed_points", fixed_points)
            if write_canonical_compat:
                _write_array_dataset(
                    handle,
                    "/steady_state/fixed_point_xyz",
                    np.transpose(fixed_points, (1, 0, 2)),
                )

        if config.output.save_profiles:
            individual_complex_realimag = np.stack(
                [individual_complex.real, individual_complex.imag],
                axis=-1,
            )
            _write_array_dataset(
                handle,
                "/profiles/individual_complex_realimag",
                individual_complex_realimag,
            )
            _write_array_dataset(handle, "/profiles/individual_abs", individual_abs)
            _write_array_dataset(handle, "/profiles/sos_abs", sos_abs)
            if write_canonical_compat:
                _write_array_dataset(
                    handle,
                    "/profiles/individual_complex",
                    np.asarray(individual_complex.T, dtype=np.complex128),
                )
                _write_array_dataset(handle, "/profiles/sos_magnitude", sos_abs)


def _require_axis(result: SimulationResult, key: str) -> np.ndarray:
    try:
        return np.asarray(result.axes[key], dtype=np.float64)
    except KeyError as exc:
        msg = f"SimulationResult is missing axis {key!r}."
        raise ValueError(msg) from exc


def _require_trajectory(result: SimulationResult, key: str) -> np.ndarray:
    try:
        return np.asarray(result.trajectories[key])
    except KeyError as exc:
        msg = f"SimulationResult is missing trajectory {key!r}."
        raise ValueError(msg) from exc


def _require_observable(result: SimulationResult, key: str) -> np.ndarray:
    try:
        return np.asarray(result.observables[key])
    except KeyError as exc:
        msg = f"SimulationResult is missing observable {key!r}."
        raise ValueError(msg) from exc


def _write_root_attrs(handle: h5py.File) -> None:
    created_at_utc = (
        datetime.now(tz=UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
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
    group.create_dataset(
        dataset_name,
        data=value,
        dtype=h5py.string_dtype(encoding="utf-8"),
    )

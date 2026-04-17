"""Adapters that isolate the GUI from Chapter 3/4/5 implementation details."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import h5py
import numpy as np
import numpy.typing as npt
import yaml

from bssfpviz.io.hdf5_store import load_dataset
from bssfpviz.models.results import SimulationDataset
from bssfpviz.models.run_config import (
    IntegrationConfig,
    MetaConfig,
    OutputConfig,
    PhaseCycleConfig,
    PhysicsConfig,
    RunConfig,
    SequenceConfig,
    SweepConfig,
)
from bssfpviz.workflows.run_compute import run_compute

if TYPE_CHECKING:
    from bssfpviz.gui.dataset_view_model import DatasetViewModel

FloatArray = npt.NDArray[np.float64]


@dataclass(slots=True)
class LoadedDatasetView:
    """GUI-friendly view of one loaded HDF5 dataset."""

    source_path: Path | None = None
    delta_f_hz: FloatArray | None = None
    rk_time_s: FloatArray | None = None
    rk_magnetization: FloatArray | None = None
    steady_state_time_s: FloatArray | None = None
    steady_state_orbit: FloatArray | None = None
    steady_state_fixed_points: FloatArray | None = None
    profiles_complex_real: FloatArray | None = None
    profiles_complex_imag: FloatArray | None = None
    profiles_sos: FloatArray | None = None
    meta: dict[str, object] = field(default_factory=dict)
    config: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.delta_f_hz = _optional_float_array(self.delta_f_hz)
        self.rk_time_s = _optional_float_array(self.rk_time_s)
        self.rk_magnetization = _optional_float_array(self.rk_magnetization)
        self.steady_state_time_s = _optional_float_array(self.steady_state_time_s)
        self.steady_state_orbit = _optional_float_array(self.steady_state_orbit)
        self.steady_state_fixed_points = _optional_float_array(self.steady_state_fixed_points)
        self.profiles_complex_real = _optional_float_array(self.profiles_complex_real)
        self.profiles_complex_imag = _optional_float_array(self.profiles_complex_imag)
        self.profiles_sos = _optional_float_array(self.profiles_sos)

    @property
    def individual_profile_magnitude(self) -> FloatArray | None:
        """Return acquisition-wise magnitude profiles with shape `(n_delta_f, n_acq)`."""
        if self.profiles_complex_real is None or self.profiles_complex_imag is None:
            return None
        return np.sqrt(self.profiles_complex_real**2 + self.profiles_complex_imag**2)


def make_default_run_config() -> RunConfig:
    """Return the default GUI config used for new documents in Chapter 5."""
    return RunConfig(
        meta=MetaConfig(case_name="chapter5_default", description="default GUI case"),
        physics=PhysicsConfig(t1_s=1.5, t2_s=1.0, m0=1.0),
        sequence=SequenceConfig(
            tr_s=0.004,
            rf_duration_s=0.001,
            n_rf=100,
            alpha_deg=60.0,
            waveform_kind="hann",
            readout_fraction_of_free=0.5,
        ),
        phase_cycles=PhaseCycleConfig(
            values_deg=np.array([[0.0, 0.0], [0.0, 180.0]], dtype=np.float64)
        ),
        sweep=SweepConfig(start_hz=-200.0, stop_hz=200.0, count=21),
        integration=IntegrationConfig(
            rk_method="RK45",
            rk_rtol=1.0e-7,
            rk_atol=1.0e-9,
            rk_max_step_s=5.0e-6,
            rk_superperiods=60,
            save_every_time_step=True,
        ),
        output=OutputConfig(
            save_profiles=True,
            save_rk_trajectories=True,
            save_steady_state_orbit=True,
            save_fixed_points=True,
        ),
    )


def load_run_config_from_yaml(path: Path) -> Any:
    """Load a Chapter 4/5 run config from YAML."""
    return RunConfig.from_yaml(path)


def save_run_config_to_yaml(config: Any, path: Path) -> None:
    """Save a Chapter 4/5 run config to YAML."""
    run_config = _coerce_run_config(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "case_name": run_config.meta.case_name,
            "description": run_config.meta.description,
        },
        "physics": {
            "T1_s": run_config.physics.t1_s,
            "T2_s": run_config.physics.t2_s,
            "M0": run_config.physics.m0,
        },
        "sequence": {
            "TR_s": run_config.sequence.tr_s,
            "rf_duration_s": run_config.sequence.rf_duration_s,
            "n_rf": run_config.sequence.n_rf,
            "alpha_deg": run_config.sequence.alpha_deg,
            "waveform_kind": run_config.sequence.waveform_kind,
            "readout_fraction_of_free": run_config.sequence.readout_fraction_of_free,
        },
        "phase_cycles": {"values_deg": run_config.phase_cycles.values_deg.tolist()},
        "sweep": {
            "delta_f_hz": {
                "start": run_config.sweep.start_hz,
                "stop": run_config.sweep.stop_hz,
                "count": run_config.sweep.count,
            }
        },
        "integration": {
            "rk_method": run_config.integration.rk_method,
            "rk_rtol": run_config.integration.rk_rtol,
            "rk_atol": run_config.integration.rk_atol,
            "rk_max_step_s": run_config.integration.rk_max_step_s,
            "rk_superperiods": run_config.integration.rk_superperiods,
            "save_every_time_step": run_config.integration.save_every_time_step,
        },
        "output": {
            "save_profiles": run_config.output.save_profiles,
            "save_rk_trajectories": run_config.output.save_rk_trajectories,
            "save_steady_state_orbit": run_config.output.save_steady_state_orbit,
            "save_fixed_points": run_config.output.save_fixed_points,
        },
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def run_compute_adapter(config: Any, output_path: Path) -> Any:
    """Run the Chapter 4 compute pipeline from the GUI."""
    return run_compute(_coerce_run_config(config), output_path)


def load_hdf5_dataset(path: Path) -> Any:
    """Load an HDF5 file and return a GUI-friendly dataset view."""
    with h5py.File(path, "r") as handle:
        if _has_preferred_alias_datasets(handle):
            return _load_alias_dataset_view(handle, path)

    try:
        canonical_dataset = load_dataset(path)
    except Exception:
        canonical_dataset = None
    if canonical_dataset is not None:
        return coerce_loaded_dataset_view(canonical_dataset, path=path)

    with h5py.File(path, "r") as handle:
        return _load_alias_dataset_view(handle, path)


def dataset_to_view_model(dataset: Any) -> DatasetViewModel:
    """Normalize any supported dataset object into a Chapter 6 view-model."""
    from bssfpviz.gui.dataset_view_model import DatasetViewModel

    if isinstance(dataset, DatasetViewModel):
        return dataset
    if isinstance(dataset, SimulationDataset):
        return DatasetViewModel.from_dataset(dataset)
    view = coerce_loaded_dataset_view(dataset)
    return DatasetViewModel.from_loaded_view(view)


def coerce_loaded_dataset_view(dataset: Any, path: Path | None = None) -> LoadedDatasetView:
    """Normalize a loaded dataset object into the GUI view model."""
    if isinstance(dataset, LoadedDatasetView):
        return dataset
    if isinstance(dataset, SimulationDataset):
        phase_cycles_deg = np.rad2deg(dataset.config.sequence.phase_schedule_rad)
        return LoadedDatasetView(
            source_path=path,
            delta_f_hz=np.asarray(dataset.config.sampling.delta_f_hz, dtype=np.float64),
            rk_time_s=np.asarray(dataset.reference_time_s, dtype=np.float64),
            rk_magnetization=np.transpose(dataset.reference_m_xyz, (1, 0, 2, 3)),
            steady_state_time_s=np.asarray(dataset.steady_state_time_s, dtype=np.float64),
            steady_state_orbit=np.transpose(dataset.steady_state_orbit_xyz, (1, 0, 2, 3)),
            steady_state_fixed_points=np.transpose(dataset.steady_state_fixed_point_xyz, (1, 0, 2)),
            profiles_complex_real=np.asarray(
                dataset.individual_profile_complex.T.real, dtype=np.float64
            ),
            profiles_complex_imag=np.asarray(
                dataset.individual_profile_complex.T.imag, dtype=np.float64
            ),
            profiles_sos=np.asarray(dataset.sos_profile_magnitude, dtype=np.float64),
            meta={
                "schema_version": dataset.metadata.schema_version,
                "created_at_utc": dataset.metadata.created_at_utc,
                "app_name": dataset.metadata.app_name,
                "app_version": dataset.metadata.app_version,
                "git_commit": dataset.metadata.git_commit,
                "case_name": dataset.metadata.run_name,
                "description": dataset.metadata.user_notes,
            },
            config={
                "physics": {
                    "T1_s": dataset.config.physics.t1_s,
                    "T2_s": dataset.config.physics.t2_s,
                    "M0": dataset.config.physics.m0,
                },
                "sequence": {
                    "TR_s": dataset.config.sequence.tr_s,
                    "rf_duration_s": dataset.config.sequence.rf_duration_s,
                    "n_rf": dataset.config.sequence.n_rf_samples,
                    "alpha_deg": float(np.rad2deg(dataset.config.sequence.flip_angle_rad)),
                    "readout_fraction_of_free": 0.5,
                    "phase_cycles_deg": phase_cycles_deg.tolist(),
                },
                "sweep": {
                    "delta_f_min_hz": float(np.min(dataset.config.sampling.delta_f_hz)),
                    "delta_f_max_hz": float(np.max(dataset.config.sampling.delta_f_hz)),
                    "delta_f_count": int(dataset.config.sampling.delta_f_hz.shape[0]),
                },
            },
        )
    if isinstance(dataset, Mapping):
        mapping = dict(dataset)
        return LoadedDatasetView(
            source_path=path,
            delta_f_hz=_mapping_array(mapping.get("delta_f_hz")),
            rk_time_s=_mapping_array(mapping.get("rk_time_s")),
            rk_magnetization=_mapping_array(mapping.get("rk_magnetization")),
            steady_state_time_s=_mapping_array(mapping.get("steady_state_time_s")),
            steady_state_orbit=_mapping_array(mapping.get("steady_state_orbit")),
            steady_state_fixed_points=_mapping_array(mapping.get("steady_state_fixed_points")),
            profiles_complex_real=_mapping_array(mapping.get("profiles_complex_real")),
            profiles_complex_imag=_mapping_array(mapping.get("profiles_complex_imag")),
            profiles_sos=_mapping_array(mapping.get("profiles_sos")),
            meta=dict(mapping.get("meta", {})),
            config=dict(mapping.get("config", {})),
        )
    msg = f"Unsupported dataset object for GUI view: {type(dataset)!r}"
    raise TypeError(msg)


def _coerce_run_config(config: Any) -> RunConfig:
    if isinstance(config, RunConfig):
        return config
    if isinstance(config, Mapping):
        return RunConfig(**dict(config))
    msg = f"Unsupported config object: {type(config)!r}"
    raise TypeError(msg)


def _optional_float_array(value: object | None) -> FloatArray | None:
    if value is None:
        return None
    return np.asarray(value, dtype=np.float64)


def _mapping_array(value: object | None) -> FloatArray | None:
    if value is None:
        return None
    return np.asarray(value, dtype=np.float64)


def _dataset_exists(handle: h5py.File, path: str) -> bool:
    return path in handle and isinstance(handle[path], h5py.Dataset)


def _read_optional_array(handle: h5py.File, path: str) -> FloatArray | None:
    if not _dataset_exists(handle, path):
        return None
    return np.asarray(handle[path][()], dtype=np.float64)


def _read_optional_complex_array(handle: h5py.File, path: str) -> npt.NDArray[np.complex128] | None:
    if not _dataset_exists(handle, path):
        return None
    return np.asarray(handle[path][()], dtype=np.complex128)


def _read_optional_string(handle: h5py.File, path: str) -> str | None:
    if not _dataset_exists(handle, path):
        return None
    return str(handle[path].asstr()[()])


def _read_optional_scalar(handle: h5py.File, path: str) -> float | int | None:
    if not _dataset_exists(handle, path):
        return None
    value = handle[path][()]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _extract_meta(handle: h5py.File, path: Path) -> dict[str, object]:
    return {
        "file_path": str(path),
        "schema_version": str(handle.attrs.get("schema_version", "")),
        "created_at_utc": str(handle.attrs.get("created_at_utc", "")),
        "app_name": str(handle.attrs.get("app_name", "")),
        "app_version": str(handle.attrs.get("app_version", "")),
        "git_commit": str(handle.attrs.get("git_commit", "")),
        "case_name": _read_optional_string(handle, "/meta/case_name")
        or _read_optional_string(handle, "/meta/run_name")
        or "",
        "description": _read_optional_string(handle, "/meta/description")
        or _read_optional_string(handle, "/meta/user_notes")
        or "",
    }


def _extract_config(handle: h5py.File, delta_f_hz: FloatArray | None) -> dict[str, object]:
    flip_angle_rad = _read_optional_scalar(handle, "/config/sequence/flip_angle_rad")
    alpha_deg = _read_optional_scalar(handle, "/config/sequence/alpha_deg")
    if alpha_deg is None and isinstance(flip_angle_rad, (float, int)):
        alpha_deg = float(np.rad2deg(float(flip_angle_rad)))

    n_rf = _read_optional_scalar(handle, "/config/sequence/n_rf")
    if n_rf is None:
        n_rf = _read_optional_scalar(handle, "/config/sequence/n_rf_samples")

    phase_cycles_deg = _read_optional_array(handle, "/config/phase_cycles/values_deg")
    if phase_cycles_deg is None:
        phase_cycles_rad = _read_optional_array(handle, "/config/sequence/phase_schedule_rad")
        if phase_cycles_rad is not None:
            phase_cycles_deg = np.rad2deg(phase_cycles_rad)

    physics = {
        "T1_s": _read_optional_scalar(handle, "/config/physics/T1_s"),
        "T2_s": _read_optional_scalar(handle, "/config/physics/T2_s"),
        "M0": _read_optional_scalar(handle, "/config/physics/M0"),
    }
    sequence = {
        "TR_s": _read_optional_scalar(handle, "/config/sequence/TR_s"),
        "rf_duration_s": _read_optional_scalar(handle, "/config/sequence/rf_duration_s"),
        "n_rf": n_rf,
        "alpha_deg": alpha_deg,
        "readout_fraction_of_free": _read_optional_scalar(
            handle, "/config/sequence/readout_fraction_of_free"
        ),
        "phase_cycles_deg": phase_cycles_deg.tolist() if phase_cycles_deg is not None else [],
    }
    sweep = {
        "delta_f_min_hz": float(np.min(delta_f_hz)) if delta_f_hz is not None else None,
        "delta_f_max_hz": float(np.max(delta_f_hz)) if delta_f_hz is not None else None,
        "delta_f_count": int(delta_f_hz.shape[0]) if delta_f_hz is not None else 0,
    }
    return {"physics": physics, "sequence": sequence, "sweep": sweep}


def _has_preferred_alias_datasets(handle: h5py.File) -> bool:
    return (_dataset_exists(handle, "/rk/time_s") and _dataset_exists(handle, "/rk/M")) or (
        _dataset_exists(handle, "/steady_state/orbit_time_s")
        and _dataset_exists(handle, "/steady_state/orbit_M")
    )


def _load_alias_dataset_view(handle: h5py.File, path: Path) -> LoadedDatasetView:
    delta_f_hz = _read_optional_array(handle, "/sweep/delta_f_hz")
    if delta_f_hz is None:
        delta_f_hz = _read_optional_array(handle, "/config/sampling/delta_f_hz")

    rk_time_s = _read_optional_array(handle, "/rk/time_s")
    rk_m = _read_optional_array(handle, "/rk/M")
    if rk_time_s is None:
        rk_time_s = _read_optional_array(handle, "/time/reference_time_s")
    if rk_m is None:
        rk_canonical = _read_optional_array(handle, "/reference/M_xyz")
        if rk_canonical is not None and rk_canonical.ndim == 4:
            rk_m = np.transpose(rk_canonical, (1, 0, 2, 3))

    steady_time_s = _read_optional_array(handle, "/steady_state/orbit_time_s")
    steady_orbit = _read_optional_array(handle, "/steady_state/orbit_M")
    fixed_points = _read_optional_array(handle, "/steady_state/fixed_points")
    if steady_time_s is None:
        steady_time_s = _read_optional_array(handle, "/time/steady_state_time_s")
    if steady_orbit is None:
        steady_canonical = _read_optional_array(handle, "/steady_state/orbit_xyz")
        if steady_canonical is not None and steady_canonical.ndim == 4:
            steady_orbit = np.transpose(steady_canonical, (1, 0, 2, 3))
    if fixed_points is None:
        fixed_canonical = _read_optional_array(handle, "/steady_state/fixed_point_xyz")
        if fixed_canonical is not None and fixed_canonical.ndim == 3:
            fixed_points = np.transpose(fixed_canonical, (1, 0, 2))

    realimag = _read_optional_array(handle, "/profiles/individual_complex_realimag")
    if realimag is not None and realimag.ndim == 3 and realimag.shape[-1] == 2:
        profiles_real = np.asarray(realimag[..., 0], dtype=np.float64)
        profiles_imag = np.asarray(realimag[..., 1], dtype=np.float64)
    else:
        canonical_complex = _read_optional_complex_array(handle, "/profiles/individual_complex")
        if canonical_complex is None:
            profiles_real = None
            profiles_imag = None
        else:
            canonical_complex = np.asarray(canonical_complex.T, dtype=np.complex128)
            profiles_real = np.asarray(canonical_complex.real, dtype=np.float64)
            profiles_imag = np.asarray(canonical_complex.imag, dtype=np.float64)

    profiles_sos = _read_optional_array(handle, "/profiles/sos_abs")
    if profiles_sos is None:
        profiles_sos = _read_optional_array(handle, "/profiles/sos_magnitude")

    meta = _extract_meta(handle, path)
    config = _extract_config(handle, delta_f_hz)
    return LoadedDatasetView(
        source_path=path,
        delta_f_hz=delta_f_hz,
        rk_time_s=rk_time_s,
        rk_magnetization=rk_m,
        steady_state_time_s=steady_time_s,
        steady_state_orbit=steady_orbit,
        steady_state_fixed_points=fixed_points,
        profiles_complex_real=profiles_real,
        profiles_complex_imag=profiles_imag,
        profiles_sos=profiles_sos,
        meta=meta,
        config=config,
    )

"""HDF5 persistence for Chapter 3 simulation datasets."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import numpy.typing as npt

from bssfpviz.models.config import (
    PhysicsConfig,
    SamplingConfig,
    SequenceConfig,
    SimulationConfig,
    SimulationMetadata,
)
from bssfpviz.models.results import SimulationDataset

FloatArray = npt.NDArray[np.float64]

SCHEMA_VERSION = "2.0"


class HDF5SchemaError(ValueError):
    """Raised when an HDF5 file does not match the expected schema."""


def save_dataset(path: str | Path, dataset: SimulationDataset) -> None:
    """Save a SimulationDataset to an HDF5 file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(output_path, "w") as handle:
        _write_root_attrs(handle, dataset.metadata)

        _write_scalar_dataset(handle, "/config/physics/T1_s", dataset.config.physics.t1_s)
        _write_scalar_dataset(handle, "/config/physics/T2_s", dataset.config.physics.t2_s)
        _write_scalar_dataset(handle, "/config/physics/M0", dataset.config.physics.m0)
        _write_scalar_dataset(
            handle,
            "/config/physics/gamma_rad_per_s_per_T",
            dataset.config.physics.gamma_rad_per_s_per_t,
        )

        _write_scalar_dataset(handle, "/config/sequence/TR_s", dataset.config.sequence.tr_s)
        _write_scalar_dataset(handle, "/config/sequence/TE_s", dataset.config.sequence.te_s)
        _write_scalar_dataset(
            handle, "/config/sequence/rf_duration_s", dataset.config.sequence.rf_duration_s
        )
        _write_scalar_dataset(
            handle, "/config/sequence/free_duration_s", dataset.config.sequence.free_duration_s
        )
        _write_scalar_dataset(
            handle, "/config/sequence/n_rf_samples", dataset.config.sequence.n_rf_samples
        )
        _write_scalar_dataset(
            handle, "/config/sequence/flip_angle_rad", dataset.config.sequence.flip_angle_rad
        )
        _write_scalar_dataset(handle, "/config/sequence/n_cycles", dataset.config.sequence.n_cycles)
        _write_array_dataset(
            handle,
            "/config/sequence/phase_schedule_rad",
            dataset.config.sequence.phase_schedule_rad,
        )

        _write_array_dataset(
            handle, "/config/sampling/delta_f_hz", dataset.config.sampling.delta_f_hz
        )
        _write_scalar_dataset(handle, "/config/sampling/rk_dt_s", dataset.config.sampling.rk_dt_s)
        _write_scalar_dataset(
            handle, "/config/sampling/steady_state_dt_s", dataset.config.sampling.steady_state_dt_s
        )
        _write_scalar_dataset(
            handle, "/config/sampling/n_reference_steps", dataset.config.sampling.n_reference_steps
        )
        _write_scalar_dataset(
            handle,
            "/config/sampling/n_steady_state_steps",
            dataset.config.sampling.n_steady_state_steps,
        )

        _write_array_dataset(handle, "/waveforms/rf_xy", dataset.rf_xy)
        _write_array_dataset(handle, "/time/reference_time_s", dataset.reference_time_s)
        _write_array_dataset(handle, "/time/steady_state_time_s", dataset.steady_state_time_s)
        _write_array_dataset(handle, "/reference/M_xyz", dataset.reference_m_xyz)
        _write_array_dataset(handle, "/steady_state/orbit_xyz", dataset.steady_state_orbit_xyz)
        _write_array_dataset(
            handle, "/steady_state/fixed_point_xyz", dataset.steady_state_fixed_point_xyz
        )
        _write_array_dataset(
            handle, "/profiles/individual_complex", dataset.individual_profile_complex
        )
        _write_array_dataset(handle, "/profiles/sos_magnitude", dataset.sos_profile_magnitude)
        _write_string_dataset(handle, "/meta/run_name", dataset.metadata.run_name)
        _write_string_dataset(handle, "/meta/user_notes", dataset.metadata.user_notes)


def load_dataset(path: str | Path) -> SimulationDataset:
    """Load a SimulationDataset from an HDF5 file."""
    input_path = Path(path)
    with h5py.File(input_path, "r") as handle:
        schema_version = str(handle.attrs.get("schema_version", ""))
        if schema_version != SCHEMA_VERSION:
            msg = f"Unsupported schema version {schema_version!r}; expected {SCHEMA_VERSION!r}."
            raise HDF5SchemaError(msg)

        metadata = SimulationMetadata(
            schema_version=schema_version,
            created_at_utc=_read_attr_string(handle, "created_at_utc"),
            app_name=_read_attr_string(handle, "app_name"),
            app_version=_read_attr_string(handle, "app_version"),
            git_commit=_read_attr_string(handle, "git_commit"),
            run_name=_read_string_dataset(handle, "/meta/run_name"),
            user_notes=_read_string_dataset(handle, "/meta/user_notes"),
        )

        config = SimulationConfig(
            physics=PhysicsConfig(
                t1_s=_read_scalar_float(handle, "/config/physics/T1_s"),
                t2_s=_read_scalar_float(handle, "/config/physics/T2_s"),
                m0=_read_scalar_float(handle, "/config/physics/M0"),
                gamma_rad_per_s_per_t=_read_scalar_float(
                    handle, "/config/physics/gamma_rad_per_s_per_T"
                ),
            ),
            sequence=SequenceConfig(
                tr_s=_read_scalar_float(handle, "/config/sequence/TR_s"),
                te_s=_read_scalar_float(handle, "/config/sequence/TE_s"),
                rf_duration_s=_read_scalar_float(handle, "/config/sequence/rf_duration_s"),
                free_duration_s=_read_scalar_float(handle, "/config/sequence/free_duration_s"),
                n_rf_samples=_read_scalar_int(handle, "/config/sequence/n_rf_samples"),
                flip_angle_rad=_read_scalar_float(handle, "/config/sequence/flip_angle_rad"),
                phase_schedule_rad=_read_array(handle, "/config/sequence/phase_schedule_rad"),
                n_cycles=_read_scalar_int(handle, "/config/sequence/n_cycles"),
            ),
            sampling=SamplingConfig(
                delta_f_hz=_read_array(handle, "/config/sampling/delta_f_hz"),
                rk_dt_s=_read_scalar_float(handle, "/config/sampling/rk_dt_s"),
                steady_state_dt_s=_read_scalar_float(handle, "/config/sampling/steady_state_dt_s"),
                n_reference_steps=_read_scalar_int(handle, "/config/sampling/n_reference_steps"),
                n_steady_state_steps=_read_scalar_int(
                    handle, "/config/sampling/n_steady_state_steps"
                ),
            ),
        )

        try:
            return SimulationDataset(
                metadata=metadata,
                config=config,
                rf_xy=_read_array(handle, "/waveforms/rf_xy"),
                reference_time_s=_read_array(handle, "/time/reference_time_s"),
                steady_state_time_s=_read_array(handle, "/time/steady_state_time_s"),
                reference_m_xyz=_read_array(handle, "/reference/M_xyz"),
                steady_state_orbit_xyz=_read_array(handle, "/steady_state/orbit_xyz"),
                steady_state_fixed_point_xyz=_read_array(handle, "/steady_state/fixed_point_xyz"),
                individual_profile_complex=np.asarray(
                    _require_dataset(handle, "/profiles/individual_complex")[()],
                    dtype=np.complex128,
                ),
                sos_profile_magnitude=_read_array(handle, "/profiles/sos_magnitude"),
            )
        except HDF5SchemaError:
            raise
        except ValueError as exc:
            msg = f"Invalid dataset contents in {input_path}."
            raise HDF5SchemaError(msg) from exc


def peek_hdf5_summary(path: str | Path) -> dict[str, object]:
    """Return a small summary of a saved HDF5 dataset."""
    input_path = Path(path)
    with h5py.File(input_path, "r") as handle:
        return {
            "schema_version": str(handle.attrs.get("schema_version", "")),
            "created_at_utc": str(handle.attrs.get("created_at_utc", "")),
            "app_name": str(handle.attrs.get("app_name", "")),
            "app_version": str(handle.attrs.get("app_version", "")),
            "git_commit": str(handle.attrs.get("git_commit", "")),
            "run_name": _read_string_dataset(handle, "/meta/run_name"),
            "n_spins": int(_require_dataset(handle, "/config/sampling/delta_f_hz").shape[0]),
            "n_acq": int(_require_dataset(handle, "/profiles/individual_complex").shape[0]),
            "n_reference_steps": int(_require_dataset(handle, "/time/reference_time_s").shape[0]),
            "n_steady_state_steps": int(
                _require_dataset(handle, "/time/steady_state_time_s").shape[0]
            ),
            "reference_shape": tuple(_require_dataset(handle, "/reference/M_xyz").shape),
            "steady_state_shape": tuple(_require_dataset(handle, "/steady_state/orbit_xyz").shape),
        }


def _write_root_attrs(handle: h5py.File, metadata: SimulationMetadata) -> None:
    handle.attrs["schema_version"] = SCHEMA_VERSION
    handle.attrs["created_at_utc"] = metadata.created_at_utc
    handle.attrs["app_name"] = metadata.app_name
    handle.attrs["app_version"] = metadata.app_version
    handle.attrs["git_commit"] = metadata.git_commit


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


def _require_dataset(handle: h5py.File, path: str) -> h5py.Dataset:
    try:
        dataset = handle[path]
    except KeyError as exc:
        msg = f"Missing required dataset: {path}"
        raise HDF5SchemaError(msg) from exc
    if not isinstance(dataset, h5py.Dataset):
        msg = f"Expected dataset at {path}"
        raise HDF5SchemaError(msg)
    return dataset


def _read_attr_string(handle: h5py.File, name: str) -> str:
    if name not in handle.attrs:
        msg = f"Missing required root attribute: {name}"
        raise HDF5SchemaError(msg)
    return str(handle.attrs[name])


def _read_string_dataset(handle: h5py.File, path: str) -> str:
    dataset = _require_dataset(handle, path)
    value = dataset.asstr()[()]
    return str(value)


def _read_scalar_float(handle: h5py.File, path: str) -> float:
    dataset = _require_dataset(handle, path)
    return float(dataset[()])


def _read_scalar_int(handle: h5py.File, path: str) -> int:
    dataset = _require_dataset(handle, path)
    return int(dataset[()])


def _read_array(handle: h5py.File, path: str) -> FloatArray:
    dataset = _require_dataset(handle, path)
    return np.asarray(dataset[()], dtype=np.float64)

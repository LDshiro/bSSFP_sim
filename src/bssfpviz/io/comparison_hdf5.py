"""HDF5 persistence for generic comparison bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from bssfpviz import __version__
from bssfpviz.models.comparison import ComparisonBundle, SequenceFamily, SimulationResult

COMPARISON_SCHEMA_KIND = "comparison_bundle"
COMPARISON_SCHEMA_VERSION = "1.0"


class ComparisonHDF5Error(ValueError):
    """Raised when a generic comparison HDF5 file is invalid."""


def save_comparison_bundle(path: str | Path, bundle: ComparisonBundle) -> None:
    """Write a ComparisonBundle to an HDF5 file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(output_path, "w") as handle:
        handle.attrs["schema_kind"] = COMPARISON_SCHEMA_KIND
        handle.attrs["comparison_schema_version"] = COMPARISON_SCHEMA_VERSION
        handle.attrs["app_name"] = "bloch-ssfp-visualizer"
        handle.attrs["app_version"] = __version__

        _write_simulation_result(handle, "/runs/a", bundle.run_a)
        _write_simulation_result(handle, "/runs/b", bundle.run_b)
        _write_string_dataset(handle, "/comparison/comparison_scope", bundle.comparison_scope)
        _write_string_dataset(
            handle,
            "/comparison/comparison_modes_json",
            json.dumps(list(bundle.comparison_modes), sort_keys=True),
        )
        for key, value in bundle.matched_constraints_summary.items():
            _write_scalar_or_string_dataset(
                handle,
                f"/comparison/matched_constraints_summary/{key}",
                value,
            )
        for key, value in bundle.derived_ratios.items():
            _write_scalar_dataset(handle, f"/comparison/derived_ratios/{key}", float(value))
        for key, value in bundle.report_metadata.items():
            _write_string_dataset(handle, f"/comparison/report_metadata/{key}", value)


def load_comparison_bundle(path: str | Path) -> ComparisonBundle:
    """Load a ComparisonBundle from HDF5."""
    input_path = Path(path)
    with h5py.File(input_path, "r") as handle:
        schema_kind = str(handle.attrs.get("schema_kind", ""))
        schema_version = str(handle.attrs.get("comparison_schema_version", ""))
        if schema_kind != COMPARISON_SCHEMA_KIND:
            msg = f"Unsupported schema_kind {schema_kind!r}; expected {COMPARISON_SCHEMA_KIND!r}."
            raise ComparisonHDF5Error(msg)
        if schema_version != COMPARISON_SCHEMA_VERSION:
            msg = (
                f"Unsupported comparison_schema_version {schema_version!r}; "
                f"expected {COMPARISON_SCHEMA_VERSION!r}."
            )
            raise ComparisonHDF5Error(msg)

        comparison_modes = json.loads(
            _read_string_dataset(handle, "/comparison/comparison_modes_json")
        )
        if not isinstance(comparison_modes, list):
            msg = "comparison_modes_json must decode to a list."
            raise ComparisonHDF5Error(msg)

        return ComparisonBundle(
            comparison_scope=_read_string_dataset(handle, "/comparison/comparison_scope"),
            comparison_modes=tuple(str(mode) for mode in comparison_modes),
            run_a=_read_simulation_result(handle, "/runs/a"),
            run_b=_read_simulation_result(handle, "/runs/b"),
            matched_constraints_summary=_read_scalar_group(
                handle, "/comparison/matched_constraints_summary"
            ),
            derived_ratios={
                key: float(value)
                for key, value in _read_scalar_group(handle, "/comparison/derived_ratios").items()
            },
            report_metadata={
                key: str(value)
                for key, value in _read_scalar_group(handle, "/comparison/report_metadata").items()
            },
        )


def _write_simulation_result(handle: h5py.File, path: str, result: SimulationResult) -> None:
    _write_string_dataset(handle, f"{path}/metadata/sequence_family", result.sequence_family.value)
    _write_string_dataset(handle, f"{path}/metadata/run_label", result.run_label)
    _write_string_dataset(handle, f"{path}/metadata/case_name", result.case_name)
    _write_string_dataset(handle, f"{path}/metadata/description", result.description)
    _write_string_dataset(
        handle,
        f"{path}/metadata/family_metadata_json",
        json.dumps(result.family_metadata, sort_keys=True),
    )
    for key, metadata_value in result.metadata.items():
        _write_string_dataset(handle, f"{path}/metadata/extra/{key}", metadata_value)
    for key, axis_value in result.axes.items():
        _write_array_dataset(handle, f"{path}/axes/{key}", np.asarray(axis_value, dtype=np.float64))
    for key, trajectory_value in result.trajectories.items():
        _write_array_dataset(handle, f"{path}/trajectories/{key}", np.asarray(trajectory_value))
    for key, observable_value in result.observables.items():
        _write_array_dataset(handle, f"{path}/observables/{key}", np.asarray(observable_value))
    for key, scalar_value in result.scalars.items():
        _write_scalar_or_string_dataset(handle, f"{path}/scalars/{key}", scalar_value)


def _read_simulation_result(handle: h5py.File, path: str) -> SimulationResult:
    family = SequenceFamily(_read_string_dataset(handle, f"{path}/metadata/sequence_family"))
    family_metadata = json.loads(
        _read_string_dataset(handle, f"{path}/metadata/family_metadata_json")
    )
    if not isinstance(family_metadata, dict):
        msg = "family_metadata_json must decode to an object."
        raise ComparisonHDF5Error(msg)
    metadata_map = {
        key: str(value)
        for key, value in _read_scalar_group(handle, f"{path}/metadata/extra").items()
    }
    axes_map = {
        key: np.asarray(dataset[()], dtype=np.float64)
        for key, dataset in _iter_group_datasets(handle, f"{path}/axes").items()
    }
    trajectories_map = {
        key: np.asarray(dataset[()])
        for key, dataset in _iter_group_datasets(handle, f"{path}/trajectories").items()
    }
    observables_map = {
        key: np.asarray(dataset[()])
        for key, dataset in _iter_group_datasets(handle, f"{path}/observables").items()
    }
    scalars_map = _read_scalar_group(handle, f"{path}/scalars")
    return SimulationResult(
        sequence_family=family,
        run_label=_read_string_dataset(handle, f"{path}/metadata/run_label"),
        case_name=_read_string_dataset(handle, f"{path}/metadata/case_name"),
        description=_read_string_dataset(handle, f"{path}/metadata/description"),
        metadata=metadata_map,
        family_metadata=family_metadata,
        axes=axes_map,
        trajectories=trajectories_map,
        observables=observables_map,
        scalars=scalars_map,
    )


def _iter_group_datasets(handle: h5py.File, path: str) -> dict[str, h5py.Dataset]:
    if path not in handle:
        return {}
    group = handle[path]
    if not isinstance(group, h5py.Group):
        msg = f"Expected group at {path}"
        raise ComparisonHDF5Error(msg)
    datasets: dict[str, h5py.Dataset] = {}
    for key, value in group.items():
        if not isinstance(value, h5py.Dataset):
            msg = f"Expected dataset at {path}/{key}"
            raise ComparisonHDF5Error(msg)
        datasets[str(key)] = value
    return datasets


def _read_scalar_group(handle: h5py.File, path: str) -> dict[str, Any]:
    datasets = _iter_group_datasets(handle, path)
    result: dict[str, Any] = {}
    for key, dataset in datasets.items():
        if h5py.check_string_dtype(dataset.dtype) is not None:
            result[key] = str(dataset.asstr()[()])
        else:
            value = dataset[()]
            if isinstance(value, np.generic):
                result[key] = value.item()
            else:
                result[key] = value
    return result


def _write_scalar_dataset(handle: h5py.File, path: str, value: float | int | bool) -> None:
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


def _write_scalar_or_string_dataset(
    handle: h5py.File,
    path: str,
    value: float | int | str | bool,
) -> None:
    if isinstance(value, str):
        _write_string_dataset(handle, path, value)
    else:
        _write_scalar_dataset(handle, path, value)


def _read_string_dataset(handle: h5py.File, path: str) -> str:
    try:
        dataset = handle[path]
    except KeyError as exc:
        msg = f"Missing required dataset: {path}"
        raise ComparisonHDF5Error(msg) from exc
    if not isinstance(dataset, h5py.Dataset):
        msg = f"Expected dataset at {path}"
        raise ComparisonHDF5Error(msg)
    return str(dataset.asstr()[()])

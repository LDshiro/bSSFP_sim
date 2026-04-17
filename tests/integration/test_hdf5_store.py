"""Integration tests for Chapter 3 HDF5 persistence."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

from bssfpviz.io.hdf5_store import (
    HDF5SchemaError,
    load_dataset,
    peek_hdf5_summary,
    save_dataset,
)


def test_hdf5_round_trip_preserves_values(tmp_path: Path, small_computed_dataset: object) -> None:
    output_path = tmp_path / "round_trip.h5"
    dataset = small_computed_dataset

    save_dataset(output_path, dataset)
    loaded = load_dataset(output_path)

    np.testing.assert_allclose(loaded.reference_m_xyz, dataset.reference_m_xyz)
    np.testing.assert_allclose(loaded.steady_state_orbit_xyz, dataset.steady_state_orbit_xyz)
    np.testing.assert_allclose(
        loaded.steady_state_fixed_point_xyz, dataset.steady_state_fixed_point_xyz
    )
    np.testing.assert_allclose(
        loaded.individual_profile_complex, dataset.individual_profile_complex
    )
    np.testing.assert_allclose(loaded.sos_profile_magnitude, dataset.sos_profile_magnitude)
    assert loaded.metadata.schema_version == "2.0"


def test_peek_hdf5_summary_returns_primary_metadata(
    tmp_path: Path, small_computed_dataset: object
) -> None:
    output_path = tmp_path / "summary.h5"
    dataset = small_computed_dataset

    save_dataset(output_path, dataset)
    summary = peek_hdf5_summary(output_path)

    assert summary["schema_version"] == "2.0"
    assert summary["run_name"] == "chapter3_demo"
    assert summary["n_acq"] == dataset.config.n_acquisitions
    assert summary["n_spins"] == dataset.config.n_spins


def test_schema_version_mismatch_raises(tmp_path: Path, small_computed_dataset: object) -> None:
    output_path = tmp_path / "bad_schema.h5"
    save_dataset(output_path, small_computed_dataset)

    with h5py.File(output_path, "a") as handle:
        handle.attrs["schema_version"] = "1.0"

    with pytest.raises(HDF5SchemaError, match="Unsupported schema version"):
        load_dataset(output_path)


def test_missing_required_dataset_raises(tmp_path: Path, small_computed_dataset: object) -> None:
    output_path = tmp_path / "missing_dataset.h5"
    save_dataset(output_path, small_computed_dataset)

    with h5py.File(output_path, "a") as handle:
        del handle["/profiles/sos_magnitude"]

    with pytest.raises(HDF5SchemaError, match="/profiles/sos_magnitude"):
        load_dataset(output_path)

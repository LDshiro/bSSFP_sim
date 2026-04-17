"""Integration tests for the full Chapter 3 compute pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from bssfpviz.io.hdf5_store import load_dataset, save_dataset
from bssfpviz.models.results import SimulationDataset
from bssfpviz.workflows.compute_dataset import compute_dataset, compute_late_cycle_error


@pytest.fixture(scope="module")
def chapter3_demo_dataset(chapter3_demo_config: object) -> SimulationDataset:
    """Compute the full Chapter 3 prompt dataset once for integration tests."""
    return compute_dataset(chapter3_demo_config)


def test_rk_late_cycle_matches_steady_state(chapter3_demo_dataset: SimulationDataset) -> None:
    assert compute_late_cycle_error(chapter3_demo_dataset) < 5.0e-5


def test_compute_dataset_round_trip_preserves_acquisition_axis(
    tmp_path: Path, chapter3_demo_dataset: SimulationDataset
) -> None:
    output_path = tmp_path / "chapter3_pipeline.h5"

    save_dataset(output_path, chapter3_demo_dataset)
    loaded = load_dataset(output_path)

    assert loaded.reference_m_xyz.shape == chapter3_demo_dataset.reference_m_xyz.shape
    assert loaded.steady_state_orbit_xyz.shape == chapter3_demo_dataset.steady_state_orbit_xyz.shape
    assert (
        loaded.steady_state_fixed_point_xyz.shape
        == chapter3_demo_dataset.steady_state_fixed_point_xyz.shape
    )
    np.testing.assert_allclose(
        loaded.individual_profile_complex, chapter3_demo_dataset.individual_profile_complex
    )

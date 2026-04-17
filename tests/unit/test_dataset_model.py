"""Tests for Chapter 3 result model validation."""

from __future__ import annotations

import numpy as np
import pytest

from bssfpviz.models.config import SimulationConfig, SimulationMetadata
from bssfpviz.models.results import SimulationDataset


def _make_valid_dataset(simulation_config: SimulationConfig) -> SimulationDataset:
    n_acq = simulation_config.n_acquisitions
    n_spins = simulation_config.n_spins
    n_ref = simulation_config.sampling.n_reference_steps
    n_steady = simulation_config.sampling.n_steady_state_steps
    n_rf = simulation_config.sequence.n_rf_samples

    rf_xy = np.zeros((n_rf, 2), dtype=np.float64)
    reference_time_s = np.linspace(0.0, 1.0, n_ref, dtype=np.float64)
    steady_state_time_s = np.linspace(0.0, 1.0, n_steady, dtype=np.float64)
    reference_m_xyz = np.zeros((n_acq, n_spins, n_ref, 3), dtype=np.float64)
    steady_state_orbit_xyz = np.zeros((n_acq, n_spins, n_steady, 3), dtype=np.float64)
    steady_state_fixed_point_xyz = np.zeros((n_acq, n_spins, 3), dtype=np.float64)
    individual_profile_complex = np.ones((n_acq, n_spins), dtype=np.complex128)
    sos_profile_magnitude = np.sqrt(np.sum(np.abs(individual_profile_complex) ** 2, axis=0))

    return SimulationDataset(
        metadata=SimulationMetadata(),
        config=simulation_config,
        rf_xy=rf_xy,
        reference_time_s=reference_time_s,
        steady_state_time_s=steady_state_time_s,
        reference_m_xyz=reference_m_xyz,
        steady_state_orbit_xyz=steady_state_orbit_xyz,
        steady_state_fixed_point_xyz=steady_state_fixed_point_xyz,
        individual_profile_complex=individual_profile_complex,
        sos_profile_magnitude=sos_profile_magnitude,
    )


def test_dataset_validation_accepts_expected_shapes(
    small_simulation_config: SimulationConfig,
) -> None:
    dataset = _make_valid_dataset(small_simulation_config)

    assert dataset.rf_xy.shape == (small_simulation_config.sequence.n_rf_samples, 2)
    assert dataset.reference_m_xyz.shape == (
        small_simulation_config.n_acquisitions,
        small_simulation_config.n_spins,
        small_simulation_config.sampling.n_reference_steps,
        3,
    )


def test_dataset_validation_rejects_bad_fixed_point_shape(
    small_simulation_config: SimulationConfig,
) -> None:
    dataset = _make_valid_dataset(small_simulation_config)

    with pytest.raises(ValueError, match="steady_state_fixed_point_xyz"):
        SimulationDataset(
            metadata=dataset.metadata,
            config=dataset.config,
            rf_xy=dataset.rf_xy,
            reference_time_s=dataset.reference_time_s,
            steady_state_time_s=dataset.steady_state_time_s,
            reference_m_xyz=dataset.reference_m_xyz,
            steady_state_orbit_xyz=dataset.steady_state_orbit_xyz,
            steady_state_fixed_point_xyz=np.zeros((2, 2, 3), dtype=np.float64),
            individual_profile_complex=dataset.individual_profile_complex,
            sos_profile_magnitude=dataset.sos_profile_magnitude,
        )

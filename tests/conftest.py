"""Pytest configuration shared by unit and integration tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bssfpviz.models.config import (  # noqa: E402
    PhysicsConfig,
    SamplingConfig,
    SequenceConfig,
    SimulationConfig,
    SimulationMetadata,
)
from bssfpviz.models.results import SimulationDataset  # noqa: E402
from bssfpviz.workflows.compute_dataset import (  # noqa: E402
    compute_dataset,
    make_chapter3_demo_config,
)


def build_test_simulation_config(
    *,
    n_rf_samples: int = 8,
    n_cycles: int = 6,
    delta_f_hz: np.ndarray | None = None,
) -> SimulationConfig:
    """Return a small Chapter 3 config for unit and lightweight integration tests."""
    if delta_f_hz is None:
        delta_f_hz = np.array([-10.0, 0.0, 10.0], dtype=np.float64)
    n_steady_state_steps = 2 * n_rf_samples + 3
    n_reference_steps = n_cycles * (n_steady_state_steps - 1) + 1

    return SimulationConfig(
        physics=PhysicsConfig(t1_s=0.050, t2_s=0.025, m0=1.0),
        sequence=SequenceConfig(
            tr_s=0.004,
            te_s=0.0025,
            rf_duration_s=0.001,
            free_duration_s=0.003,
            n_rf_samples=n_rf_samples,
            flip_angle_rad=float(np.pi / 4.0),
            phase_schedule_rad=np.array([[0.0, 0.0], [0.0, np.pi]], dtype=np.float64),
            n_cycles=n_cycles,
        ),
        sampling=SamplingConfig(
            delta_f_hz=np.asarray(delta_f_hz, dtype=np.float64),
            rk_dt_s=2.0e-5,
            steady_state_dt_s=2.0e-5,
            n_reference_steps=n_reference_steps,
            n_steady_state_steps=n_steady_state_steps,
        ),
    )


def build_test_simulation_dataset(
    config: SimulationConfig | None = None,
) -> SimulationDataset:
    """Return a small canonical dataset for GUI playback tests."""
    simulation_config = config or build_test_simulation_config()
    n_acq = simulation_config.n_acquisitions
    n_spins = simulation_config.n_spins
    n_reference = simulation_config.sampling.n_reference_steps
    n_steady = simulation_config.sampling.n_steady_state_steps
    n_rf = simulation_config.sequence.n_rf_samples

    reference_time_s = np.linspace(0.0, 2.0e-3 * (n_reference - 1), n_reference, dtype=np.float64)
    steady_time_s = np.linspace(
        0.0,
        simulation_config.superperiod_duration_s,
        n_steady,
        dtype=np.float64,
    )
    rf_xy = np.zeros((n_rf, 2), dtype=np.float64)
    rf_xy[:, 0] = np.linspace(0.0, 1.0, n_rf, dtype=np.float64)

    reference_m_xyz = np.zeros((n_acq, n_spins, n_reference, 3), dtype=np.float64)
    steady_state_orbit_xyz = np.zeros((n_acq, n_spins, n_steady, 3), dtype=np.float64)
    steady_state_fixed_point_xyz = np.zeros((n_acq, n_spins, 3), dtype=np.float64)

    for acquisition_index in range(n_acq):
        for spin_index in range(n_spins):
            phase = 0.35 * acquisition_index + 0.20 * spin_index
            reference_m_xyz[acquisition_index, spin_index, :, 0] = np.cos(
                2.0 * np.pi * reference_time_s / reference_time_s[-1] + phase
            )
            reference_m_xyz[acquisition_index, spin_index, :, 1] = np.sin(
                2.0 * np.pi * reference_time_s / reference_time_s[-1] + phase
            )
            reference_m_xyz[acquisition_index, spin_index, :, 2] = np.linspace(
                1.0,
                0.25 + 0.1 * acquisition_index + 0.05 * spin_index,
                n_reference,
                dtype=np.float64,
            )

            steady_state_orbit_xyz[acquisition_index, spin_index, :, 0] = np.cos(
                2.0 * np.pi * steady_time_s / steady_time_s[-1] + phase
            )
            steady_state_orbit_xyz[acquisition_index, spin_index, :, 1] = np.sin(
                2.0 * np.pi * steady_time_s / steady_time_s[-1] + phase
            )
            steady_state_orbit_xyz[acquisition_index, spin_index, :, 2] = 0.25 + 0.1 * np.cos(
                2.0 * np.pi * steady_time_s / steady_time_s[-1] + phase
            )
            steady_state_fixed_point_xyz[acquisition_index, spin_index, :] = steady_state_orbit_xyz[
                acquisition_index, spin_index, 0, :
            ]

    individual_profile_complex = np.zeros((n_acq, n_spins), dtype=np.complex128)
    for acquisition_index in range(n_acq):
        magnitude = np.linspace(1.0 + acquisition_index, 2.0 + acquisition_index, n_spins)
        phase = np.linspace(0.0, np.pi / 2.0, n_spins) + 0.1 * acquisition_index
        individual_profile_complex[acquisition_index, :] = magnitude * np.exp(1j * phase)
    sos_profile_magnitude = np.sqrt(np.sum(np.abs(individual_profile_complex) ** 2, axis=0))

    return SimulationDataset(
        metadata=SimulationMetadata(run_name="gui_test_dataset"),
        config=simulation_config,
        rf_xy=rf_xy,
        reference_time_s=reference_time_s,
        steady_state_time_s=steady_time_s,
        reference_m_xyz=reference_m_xyz,
        steady_state_orbit_xyz=steady_state_orbit_xyz,
        steady_state_fixed_point_xyz=steady_state_fixed_point_xyz,
        individual_profile_complex=individual_profile_complex,
        sos_profile_magnitude=sos_profile_magnitude,
    )


@pytest.fixture(scope="session")
def qapp() -> object:
    """Provide a QApplication that can run in headless test environments."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def small_simulation_config() -> SimulationConfig:
    """Provide a small, fast Chapter 3 simulation config."""
    return build_test_simulation_config()


@pytest.fixture(scope="session")
def chapter3_demo_config() -> SimulationConfig:
    """Provide the exact Chapter 3 prompt configuration."""
    return make_chapter3_demo_config()


@pytest.fixture
def small_simulation_dataset(small_simulation_config: SimulationConfig) -> SimulationDataset:
    """Provide a small canonical dataset for GUI playback tests."""
    return build_test_simulation_dataset(small_simulation_config)


@pytest.fixture(scope="session")
def small_computed_dataset() -> SimulationDataset:
    """Provide one computed Chapter 3 dataset for tests that need real solver output."""
    return compute_dataset(build_test_simulation_config())

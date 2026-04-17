"""Tests for Chapter 3 configuration models."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from bssfpviz.models.config import (
    AppConfig,
    ProjectConfig,
    SamplingConfig,
    SequenceConfig,
    SimulationConfig,
    load_app_config,
    load_project_config,
    load_simulation_config,
)


def test_app_config_defaults() -> None:
    config = AppConfig()

    assert config.window_title == "Bloch / bSSFP Visualizer - Chapter 3"
    assert config.placeholder_text == "Chapter 3 exact Bloch / steady-state pipeline"


def test_simulation_config_defaults() -> None:
    config = SimulationConfig()

    assert config.sequence.phase_schedule_rad.shape == (2, 2)
    assert config.sampling.delta_f_hz.dtype == np.float64
    assert config.n_acquisitions == 2
    assert config.sampling.n_steady_state_steps == 203
    assert config.sampling.n_reference_steps == 24_241


def test_project_config_defaults() -> None:
    config = ProjectConfig()

    assert config.app.window_width == 960
    assert config.simulation.n_spins == 3


def test_load_project_config_from_yaml() -> None:
    config_path = Path("examples/configs/minimal.yaml")

    config = load_project_config(config_path)

    assert config.app.window_title == "Bloch / bSSFP Visualizer - Chapter 3"
    assert config.simulation.sequence.n_rf_samples == 100
    assert np.isclose(config.simulation.sequence.flip_angle_rad, np.pi / 3.0)
    assert config.simulation.sequence.phase_schedule_rad.shape == (2, 2)


def test_load_simulation_config_from_yaml() -> None:
    config_path = Path("examples/configs/minimal.yaml")

    config = load_simulation_config(config_path)

    assert config.phase_schedule_rad.shape == (2, 2)
    assert config.n_spins == 3
    assert config.sampling.n_steady_state_steps == 203


def test_load_app_config_from_yaml() -> None:
    config_path = Path("examples/configs/minimal.yaml")

    config = load_app_config(config_path)

    assert config.window_title == "Bloch / bSSFP Visualizer - Chapter 3"


def test_sampling_config_rejects_non_vector_delta_f() -> None:
    with pytest.raises(ValueError, match="delta_f_hz"):
        SamplingConfig(delta_f_hz=np.zeros((2, 2), dtype=np.float64))


def test_sequence_config_requires_two_pulses_per_superperiod() -> None:
    with pytest.raises(ValueError, match="phase_schedule_rad"):
        SequenceConfig(phase_schedule_rad=np.zeros((2, 3), dtype=np.float64))


def test_simulation_config_rejects_mismatched_time_step_counts() -> None:
    with pytest.raises(ValueError, match="n_reference_steps"):
        SimulationConfig(
            sequence=SequenceConfig(n_rf_samples=8, n_cycles=4),
            sampling=SamplingConfig(
                delta_f_hz=np.array([-5.0, 0.0, 5.0], dtype=np.float64),
                rk_dt_s=1.0e-5,
                steady_state_dt_s=1.0e-5,
                n_reference_steps=99,
                n_steady_state_steps=19,
            ),
        )

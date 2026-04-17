"""Tests for the Chapter 4 CLI run-configuration models."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from bssfpviz.models.run_config import PhaseCycleConfig, RunConfig, SequenceConfig, SweepConfig


def test_run_config_from_yaml_loads_example_file() -> None:
    config = RunConfig.from_yaml(Path("examples/configs/chapter4_default.yaml"))

    assert config.meta.case_name == "chapter4_default"
    assert config.sequence.waveform_kind == "hann"
    assert config.phase_cycles.values_deg.shape == (2, 2)
    assert config.integration.rk_superperiods == 60


def test_build_delta_f_hz_returns_expected_endpoints() -> None:
    sweep = SweepConfig(start_hz=-200.0, stop_hz=200.0, count=21)

    delta_f_hz = sweep.build_delta_f_hz()

    assert delta_f_hz.shape == (21,)
    assert delta_f_hz[0] == pytest.approx(-200.0)
    assert delta_f_hz[-1] == pytest.approx(200.0)


def test_phase_cycle_degree_to_radian_conversion() -> None:
    phase_cycles = PhaseCycleConfig(values_deg=np.array([[0.0, 180.0]], dtype=np.float64))

    values_rad = phase_cycles.build_values_rad()

    np.testing.assert_allclose(values_rad, np.array([[0.0, np.pi]], dtype=np.float64))


def test_sequence_config_rejects_invalid_waveform_kind() -> None:
    with pytest.raises(ValueError, match="waveform_kind"):
        SequenceConfig(
            tr_s=0.004,
            rf_duration_s=0.001,
            n_rf=16,
            alpha_deg=60.0,
            waveform_kind="triangle",
            readout_fraction_of_free=0.5,
        )


def test_sequence_config_rejects_invalid_readout_fraction() -> None:
    with pytest.raises(ValueError, match="readout_fraction_of_free"):
        SequenceConfig(
            tr_s=0.004,
            rf_duration_s=0.001,
            n_rf=16,
            alpha_deg=60.0,
            waveform_kind="rect",
            readout_fraction_of_free=1.5,
        )


def test_sequence_config_rejects_non_positive_free_interval() -> None:
    with pytest.raises(ValueError, match="TR_s"):
        SequenceConfig(
            tr_s=0.001,
            rf_duration_s=0.001,
            n_rf=16,
            alpha_deg=60.0,
            waveform_kind="rect",
            readout_fraction_of_free=0.5,
        )


def test_sweep_config_rejects_non_positive_count() -> None:
    with pytest.raises(ValueError, match="count"):
        SweepConfig(start_hz=-1.0, stop_hz=1.0, count=0)

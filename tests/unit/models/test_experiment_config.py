"""Tests for generic comparison experiment models."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from bssfpviz.models.comparison import ExperimentConfig, SequenceFamily


def test_experiment_config_from_yaml_loads_bssfp_branches(tmp_path: Path) -> None:
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(_experiment_text(), encoding="utf-8")

    config = ExperimentConfig.from_yaml(config_path)

    assert config.comparison_scope == "physics_only"
    assert config.run_a.sequence_family == SequenceFamily.BSSFP
    assert config.run_b.sequence_family == SequenceFamily.BSSFP
    assert config.run_a.bssfp is not None
    assert config.run_a.bssfp.sequence.waveform_kind == "rect"
    assert config.run_b.bssfp is not None
    assert config.run_b.bssfp.case_name == "branch_b"
    assert config.comparison_modes == ("matched_resolution", "matched_voxel")


def test_experiment_config_rejects_invalid_comparison_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_experiment.yaml"
    config_path.write_text(
        _experiment_text().replace("matched_voxel", "unsupported_mode"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported comparison_modes"):
        ExperimentConfig.from_yaml(config_path)


def test_experiment_config_validate_supported_families_rejects_unimplemented_branch(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "unsupported_family.yaml"
    config_path.write_text(
        _experiment_text().replace("sequence_family: BSSFP", "sequence_family: FASTSE", 1),
        encoding="utf-8",
    )

    config = ExperimentConfig.from_yaml(config_path)

    with pytest.raises(ValueError, match="Unsupported sequence families"):
        config.validate_supported_families({SequenceFamily.BSSFP})


def _experiment_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_resolution
          - matched_voxel

        common_physics:
          T1_s: 1.5
          T2_s: 1.0
          M0: 1.0

        run_a:
          sequence_family: BSSFP
          label: branch_a
          bssfp:
            case_name: branch_a
            sequence:
              TR_s: 0.004
              rf_duration_s: 0.001
              n_rf: 8
              alpha_deg: 45.0
              waveform_kind: rect
              readout_fraction_of_free: 0.5
            phase_cycles:
              values_deg:
                - [0.0, 0.0]
                - [0.0, 180.0]
            sweep:
              delta_f_hz:
                start: -10.0
                stop: 10.0
                count: 3

        run_b:
          sequence_family: BSSFP
          label: branch_b
          bssfp:
            case_name: branch_b
            sequence:
              TR_s: 0.004
              rf_duration_s: 0.001
              n_rf: 8
              alpha_deg: 50.0
              waveform_kind: rect
              readout_fraction_of_free: 0.5
            phase_cycles:
              values_deg:
                - [0.0, 0.0]
                - [0.0, 180.0]
            sweep:
              delta_f_hz:
                start: -10.0
                stop: 10.0
                count: 3
        """
    ).strip()

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
        _vfa_fse_experiment_text(),
        encoding="utf-8",
    )

    config = ExperimentConfig.from_yaml(config_path)

    with pytest.raises(ValueError, match="Unsupported sequence families"):
        config.validate_supported_families({SequenceFamily.BSSFP, SequenceFamily.FASTSE})


def test_experiment_config_from_yaml_loads_fastse_branches(tmp_path: Path) -> None:
    config_path = tmp_path / "fastse_experiment.yaml"
    config_path.write_text(_fastse_experiment_text(), encoding="utf-8")

    config = ExperimentConfig.from_yaml(config_path)

    assert config.comparison_scope == "physics_only"
    assert config.run_a.sequence_family == SequenceFamily.FASTSE
    assert config.run_b.sequence_family == SequenceFamily.FASTSE
    assert config.run_a.fastse is not None
    assert config.run_a.fastse.alpha_ref_const_deg == 180.0
    assert config.run_b.fastse is not None
    assert config.run_b.fastse.etl == 4


def test_experiment_config_rejects_fastse_protocol_realistic_scope(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_fastse_scope.yaml"
    config_path.write_text(
        _fastse_experiment_text().replace(
            "comparison_scope: physics_only",
            "comparison_scope: protocol_realistic",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="FASTSE baseline currently supports"):
        ExperimentConfig.from_yaml(config_path)


def test_experiment_config_rejects_fastse_unsupported_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_fastse_mode.yaml"
    config_path.write_text(
        _fastse_experiment_text().replace("matched_resolution", "matched_scan_time"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="FASTSE baseline does not support"):
        ExperimentConfig.from_yaml(config_path)


def test_experiment_config_rejects_fastse_invalid_timing_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_fastse_timing.yaml"
    config_path.write_text(
        _fastse_experiment_text().replace(
            "timing_mode: user_fixed_ESP",
            "timing_mode: derive_min_ESP",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="timing_mode must be one of"):
        ExperimentConfig.from_yaml(config_path)


def test_experiment_config_from_yaml_loads_vfa_fse_branches(tmp_path: Path) -> None:
    config_path = tmp_path / "vfa_fse_experiment.yaml"
    config_path.write_text(_vfa_fse_experiment_text(), encoding="utf-8")

    config = ExperimentConfig.from_yaml(config_path)

    assert config.comparison_scope == "physics_only"
    assert config.run_a.sequence_family == SequenceFamily.VFA_FSE
    assert config.run_b.sequence_family == SequenceFamily.VFA_FSE
    assert config.run_a.vfa_fse is not None
    assert config.run_a.vfa_fse.etl == 4
    assert config.run_a.vfa_fse.phi_ref_train_deg is not None
    assert config.run_a.vfa_fse.phi_ref_train_deg.tolist() == [90.0, 90.0, 90.0, 90.0]
    assert config.run_b.vfa_fse is not None
    assert config.run_b.vfa_fse.phi_ref_train_deg.tolist() == [90.0, 110.0, 130.0, 150.0]


def test_experiment_config_rejects_vfa_fse_protocol_realistic_scope(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_vfa_scope.yaml"
    config_path.write_text(
        _vfa_fse_experiment_text().replace(
            "comparison_scope: physics_only",
            "comparison_scope: protocol_realistic",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="VFA_FSE_MANUAL currently supports"):
        ExperimentConfig.from_yaml(config_path)


def test_experiment_config_allows_vfa_fse_matched_te_contrast_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "vfa_te_mode.yaml"
    config_path.write_text(
        _vfa_fse_experiment_text().replace("matched_resolution", "matched_TE_contrast"),
        encoding="utf-8",
    )

    config = ExperimentConfig.from_yaml(config_path)

    assert "matched_TE_contrast" in config.comparison_modes


def test_experiment_config_rejects_vfa_fse_scan_time_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_vfa_mode.yaml"
    config_path.write_text(
        _vfa_fse_experiment_text().replace("matched_resolution", "matched_scan_time"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="VFA_FSE_MANUAL does not support"):
        ExperimentConfig.from_yaml(config_path)


def test_experiment_config_rejects_vfa_fse_phase_length_mismatch(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_vfa_phase.yaml"
    config_path.write_text(
        _vfa_fse_experiment_text().replace(
            "      - 130.0\n      - 150.0\n    esp_ms",
            "    esp_ms",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must have the same shape"):
        ExperimentConfig.from_yaml(config_path)


def test_experiment_config_rejects_vfa_fse_invalid_timing_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_vfa_timing.yaml"
    config_path.write_text(
        _vfa_fse_experiment_text().replace(
            "timing_mode: user_fixed_ESP",
            "timing_mode: derive_min_ESP",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="timing_mode must be one of"):
        ExperimentConfig.from_yaml(config_path)


def test_experiment_config_allows_fastse_vfa_mixed_family_compare(tmp_path: Path) -> None:
    config_path = tmp_path / "mixed_fastse_vfa.yaml"
    config_path.write_text(_mixed_fastse_vfa_experiment_text(), encoding="utf-8")

    config = ExperimentConfig.from_yaml(config_path)

    assert config.run_a.sequence_family == SequenceFamily.FASTSE
    assert config.run_b.sequence_family == SequenceFamily.VFA_FSE
    assert "matched_TE_contrast" in config.comparison_modes


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


def _fastse_experiment_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_resolution
          - matched_voxel

        common_physics:
          T1_s: 1000000000.0
          T2_s: 1000000000.0
          M0: 1.0

        run_a:
          sequence_family: FASTSE
          label: fastse_a
          fastse:
            case_name: fastse_a
            description: fastse left
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_const_deg: 180.0
            phi_ref_deg: 90.0
            etl: 4
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d

        run_b:
          sequence_family: FASTSE
          label: fastse_b
          fastse:
            case_name: fastse_b
            description: fastse right
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_const_deg: 120.0
            phi_ref_deg: 90.0
            etl: 4
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d
        """
    ).strip()


def _vfa_fse_experiment_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_resolution
          - matched_voxel

        common_physics:
          T1_s: 1000000000.0
          T2_s: 1000000000.0
          M0: 1.0

        run_a:
          sequence_family: VFA_FSE
          label: vfa_a
          vfa_fse:
            case_name: vfa_a
            description: manual vfa left
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_train_deg:
              - 180.0
              - 150.0
              - 120.0
              - 90.0
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d

        run_b:
          sequence_family: VFA_FSE
          label: vfa_b
          vfa_fse:
            case_name: vfa_b
            description: manual vfa right
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_train_deg:
              - 150.0
              - 130.0
              - 110.0
              - 90.0
            phi_ref_train_deg:
              - 90.0
              - 110.0
              - 130.0
              - 150.0
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d
        """
    ).strip()


def _mixed_fastse_vfa_experiment_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_TE_contrast

        common_physics:
          T1_s: 1.2
          T2_s: 0.08
          M0: 1.0

        run_a:
          sequence_family: FASTSE
          label: fastse_a
          fastse:
            case_name: fastse_a
            description: fastse left
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_const_deg: 120.0
            phi_ref_deg: 90.0
            etl: 4
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d

        run_b:
          sequence_family: VFA_FSE
          label: vfa_b
          vfa_fse:
            case_name: vfa_b
            description: vfa right
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_train_deg:
              - 150.0
              - 130.0
              - 110.0
              - 90.0
            phi_ref_train_deg:
              - 90.0
              - 100.0
              - 110.0
              - 120.0
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d
        """
    ).strip()

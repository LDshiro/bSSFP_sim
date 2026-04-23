"""Integration tests for the sequence preview CLI."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from bssfpviz.workflows.preview_cli import main


def test_preview_cli_generates_fastse_preview_json(tmp_path: Path) -> None:
    config_path = tmp_path / "preview_fastse.yaml"
    output_path = tmp_path / "preview_fastse.json"
    config_path.write_text(_fastse_preview_config_text(), encoding="utf-8")

    exit_code = main(
        [
            "--config",
            str(config_path),
            "--run",
            "both",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["comparison_scope"] == "physics_only"
    assert set(payload["runs"].keys()) == {"run_a", "run_b"}
    assert payload["runs"]["run_a"]["sequence_family"] == "FASTSE"
    assert payload["runs"]["run_a"]["family_preview"]["sample_count_echo"] == 4
    assert payload["runs"]["run_a"]["timing_summary"]["te_contrast_definition"] == "TE_center-k"
    assert payload["runs"]["run_b"]["timing_summary"]["te_contrast_definition"] == "WH2006"
    assert payload["runs"]["run_b"]["timing_summary"]["ft_wh2006"] > 0.0
    assert payload["runs"]["run_b"]["timing_summary"]["te_contrast_wh_ms"] > 0.0


def test_preview_cli_generates_bssfp_preview_json(tmp_path: Path) -> None:
    config_path = tmp_path / "preview_bssfp.yaml"
    output_path = tmp_path / "preview_bssfp.json"
    config_path.write_text(_bssfp_preview_config_text(), encoding="utf-8")

    exit_code = main(
        [
            "--config",
            str(config_path),
            "--run",
            "run_a",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(payload["runs"].keys()) == {"run_a"}
    run_a = payload["runs"]["run_a"]
    assert run_a["sequence_family"] == "BSSFP"
    assert run_a["timing_summary"]["tr_ms"] == 4.0
    assert run_a["family_preview"]["delta_f_hz"]["count"] == 3


def test_preview_cli_generates_vfa_fse_preview_json(tmp_path: Path) -> None:
    config_path = tmp_path / "preview_vfa_fse.yaml"
    output_path = tmp_path / "preview_vfa_fse.json"
    config_path.write_text(_vfa_fse_preview_config_text(), encoding="utf-8")

    exit_code = main(
        [
            "--config",
            str(config_path),
            "--run",
            "run_a",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(payload["runs"].keys()) == {"run_a"}
    run_a = payload["runs"]["run_a"]
    assert run_a["sequence_family"] == "VFA_FSE"
    assert run_a["family_preview"]["sample_count_echo"] == 4
    assert run_a["family_preview"]["phase_train_deg"] == [0.0, 90.0, 90.0, 90.0, 90.0]
    assert run_a["timing_summary"]["te_contrast_definition"] == "Busse"
    assert run_a["timing_summary"]["te_equiv_busse_ms"] >= 0.0
    assert run_a["timing_summary"]["ft_wh2006"] >= 0.0
    assert run_a["timing_summary"]["te_contrast_wh_ms"] >= 0.0
    assert run_a["timing_summary"]["te_contrast_ms"] >= 0.0
    assert len(run_a["family_preview"]["te_equiv_busse_ms_per_echo"]) == 4
    assert len(run_a["family_preview"]["ft_wh2006_per_echo"]) == 4
    assert len(run_a["family_preview"]["te_contrast_wh_ms_per_echo"]) == 4
    assert (
        run_a["warnings"][1]
        == "Busse contrast-equivalent TE is derived from an internal no-relaxation rerun."
    )


def _fastse_preview_config_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_resolution

        common_physics:
          T1_s: 1.2
          T2_s: 0.08
          M0: 1.0

        run_a:
          sequence_family: FASTSE
          label: fastse_a
          fastse:
            case_name: fastse_a
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


def _bssfp_preview_config_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_resolution

        common_physics:
          T1_s: 1.5
          T2_s: 1.0
          M0: 1.0

        run_a:
          sequence_family: BSSFP
          label: compare_a
          bssfp:
            case_name: compare_a
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
                start: -20.0
                stop: 20.0
                count: 3

        run_b:
          sequence_family: BSSFP
          label: compare_b
          bssfp:
            case_name: compare_b
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
                start: -20.0
                stop: 20.0
                count: 3
        """
    ).strip()


def _vfa_fse_preview_config_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_resolution

        common_physics:
          T1_s: 1.2
          T2_s: 0.08
          M0: 1.0

        run_a:
          sequence_family: VFA_FSE
          label: vfa_a
          vfa_fse:
            case_name: vfa_a
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

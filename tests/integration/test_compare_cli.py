"""Integration tests for the generic comparison CLI."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import h5py

from bssfpviz.io.comparison_hdf5 import load_comparison_bundle
from bssfpviz.workflows.compare_cli import main


def test_compare_cli_generates_generic_comparison_bundle(tmp_path: Path) -> None:
    config_path = tmp_path / "compare_bssfp.yaml"
    output_path = tmp_path / "compare_bssfp.h5"
    summary_json_path = tmp_path / "compare_bssfp_summary.json"
    config_path.write_text(_compare_config_text(), encoding="utf-8")

    exit_code = main(
        [
            "--config",
            str(config_path),
            "--output",
            str(output_path),
            "--summary-json",
            str(summary_json_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert summary_json_path.exists()

    with h5py.File(output_path, "r") as handle:
        assert handle.attrs["schema_kind"] == "comparison_bundle"
        assert "/runs/a/axes/delta_f_hz" in handle
        assert "/runs/b/observables/sos_abs" in handle
        assert "/comparison/derived_ratios/sos_peak_ratio_b_over_a" in handle

    summary = json.loads(summary_json_path.read_text(encoding="utf-8"))
    assert summary["comparison_scope"] == "physics_only"
    assert summary["run_a_family"] == "BSSFP"
    assert summary["run_b_family"] == "BSSFP"
    assert "derived_ratios" in summary
    assert "matched_constraints_summary" in summary

    bundle = load_comparison_bundle(output_path)
    assert bundle.run_a.case_name == "compare_a"
    assert bundle.run_b.case_name == "compare_b"


def test_compare_cli_generates_fastse_comparison_bundle(tmp_path: Path) -> None:
    config_path = tmp_path / "compare_fastse.yaml"
    output_path = tmp_path / "compare_fastse.h5"
    summary_json_path = tmp_path / "compare_fastse_summary.json"
    config_path.write_text(_compare_fastse_config_text(), encoding="utf-8")

    exit_code = main(
        [
            "--config",
            str(config_path),
            "--output",
            str(output_path),
            "--summary-json",
            str(summary_json_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert summary_json_path.exists()

    with h5py.File(output_path, "r") as handle:
        assert handle.attrs["schema_kind"] == "comparison_bundle"
        assert "/runs/a/axes/echo_time_s" in handle
        assert "/runs/b/observables/fid_signal_abs" in handle
        assert "/comparison/derived_ratios/echo_peak_ratio_b_over_a" in handle

    summary = json.loads(summary_json_path.read_text(encoding="utf-8"))
    assert summary["run_a_family"] == "FASTSE"
    assert summary["run_b_family"] == "FASTSE"
    assert summary["matched_constraints_summary"]["delta_etl"] == 0

    bundle = load_comparison_bundle(output_path)
    assert bundle.run_a.case_name == "fastse_a"
    assert bundle.run_b.case_name == "fastse_b"


def test_compare_cli_rejects_mixed_family_compare(tmp_path: Path) -> None:
    config_path = tmp_path / "mixed_compare.yaml"
    output_path = tmp_path / "mixed_compare.h5"
    config_path.write_text(_mixed_family_config_text(), encoding="utf-8")

    exit_code = main(
        [
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 1
    assert not output_path.exists()


def _compare_config_text() -> str:
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
            description: left branch
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
            integration:
              rk_method: PROPAGATOR
              rk_superperiods: 2
              rk_rtol: 1.0e-6
              rk_atol: 1.0e-8
              rk_max_step_s: 1.0e-4
              save_every_time_step: true

        run_b:
          sequence_family: BSSFP
          label: compare_b
          bssfp:
            case_name: compare_b
            description: right branch
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
            integration:
              rk_method: RK45
              rk_superperiods: 2
              rk_rtol: 1.0e-6
              rk_atol: 1.0e-8
              rk_max_step_s: 1.0e-4
              save_every_time_step: true
        """
    ).strip()


def _compare_fastse_config_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_resolution

        common_physics:
          T1_s: 1000000000.0
          T2_s: 1000000000.0
          M0: 1.0

        run_a:
          sequence_family: FASTSE
          label: fastse_a
          fastse:
            case_name: fastse_a
            description: left branch
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
            description: right branch
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


def _mixed_family_config_text() -> str:
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

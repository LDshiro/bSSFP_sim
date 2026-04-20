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

    bundle = load_comparison_bundle(output_path)
    assert bundle.run_a.case_name == "compare_a"
    assert bundle.run_b.case_name == "compare_b"


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

"""Integration tests for generic comparison bundle persistence."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from bssfpviz.io.comparison_hdf5 import load_comparison_bundle, save_comparison_bundle
from bssfpviz.models.comparison import ComparisonBundle
from bssfpviz.models.run_config import RunConfig
from bssfpviz.sequences.bssfp.runner import run_bssfp_simulation


def test_comparison_bundle_round_trip_preserves_runs(tmp_path: Path) -> None:
    config_path = tmp_path / "small_compute.yaml"
    config_path.write_text(_small_config_text(), encoding="utf-8")
    run_config = RunConfig.from_yaml(config_path)
    run_a = run_bssfp_simulation(run_config, run_label="run_a")
    run_b = run_bssfp_simulation(run_config, run_label="run_b")
    bundle = ComparisonBundle(
        comparison_scope="physics_only",
        comparison_modes=("matched_resolution",),
        run_a=run_a,
        run_b=run_b,
        matched_constraints_summary={"delta_n_delta_f": 0},
        derived_ratios={"sos_peak_ratio_b_over_a": 1.0},
        report_metadata={"status": "ok"},
    )
    output_path = tmp_path / "comparison_bundle.h5"

    save_comparison_bundle(output_path, bundle)
    loaded = load_comparison_bundle(output_path)

    assert loaded.run_a.sequence_family.value == "BSSFP"
    assert loaded.run_b.run_label == "run_b"
    np.testing.assert_allclose(loaded.run_a.axes["delta_f_hz"], run_a.axes["delta_f_hz"])
    np.testing.assert_allclose(
        loaded.run_a.observables["sos_abs"],
        run_a.observables["sos_abs"],
    )
    assert loaded.derived_ratios["sos_peak_ratio_b_over_a"] == 1.0


def _small_config_text() -> str:
    return """
meta:
  case_name: "chapter4_small"
  description: "small integration-test case"

physics:
  T1_s: 1.5
  T2_s: 1.0
  M0: 1.0

sequence:
  TR_s: 0.004
  rf_duration_s: 0.001
  n_rf: 8
  alpha_deg: 45.0
  waveform_kind: "rect"
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
  rk_method: "PROPAGATOR"
  rk_rtol: 1.0e-6
  rk_atol: 1.0e-8
  rk_max_step_s: 1.0e-4
  rk_superperiods: 2
  save_every_time_step: true

output:
  save_profiles: true
  save_rk_trajectories: true
  save_steady_state_orbit: true
  save_fixed_points: true
""".strip()

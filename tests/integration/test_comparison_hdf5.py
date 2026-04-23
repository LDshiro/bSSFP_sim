"""Integration tests for generic comparison bundle persistence."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from bssfpviz.io.comparison_hdf5 import load_comparison_bundle, save_comparison_bundle
from bssfpviz.models.comparison import (
    CommonPhysicsConfig,
    ComparisonBundle,
    FastSEFamilyConfig,
    VFAFSEFamilyConfig,
)
from bssfpviz.models.run_config import RunConfig
from bssfpviz.sequences.bssfp.runner import run_bssfp_simulation
from bssfpviz.sequences.fastse.runner import run_fastse_simulation
from bssfpviz.sequences.vfa_fse.runner import run_vfa_fse_simulation


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


def test_comparison_bundle_round_trip_preserves_fastse_runs(tmp_path: Path) -> None:
    family_config = FastSEFamilyConfig(
        case_name="fastse_case",
        description="fastse comparison round-trip",
        alpha_exc_deg=90.0,
        phi_exc_deg=0.0,
        alpha_ref_const_deg=120.0,
        phi_ref_deg=90.0,
        etl=4,
        esp_ms=8.0,
        te_nominal_ms=16.0,
        n_iso=101,
        off_resonance_hz=0.0,
    )
    physics = CommonPhysicsConfig(t1_s=1.2, t2_s=0.08, m0=1.0)
    run_a = run_fastse_simulation(family_config, physics, run_label="run_a")
    run_b = run_fastse_simulation(family_config, physics, run_label="run_b")
    bundle = ComparisonBundle(
        comparison_scope="physics_only",
        comparison_modes=("matched_resolution",),
        run_a=run_a,
        run_b=run_b,
        matched_constraints_summary={"delta_etl": 0},
        derived_ratios={"echo_peak_ratio_b_over_a": 1.0},
        report_metadata={"status": "ok"},
    )
    output_path = tmp_path / "fastse_comparison_bundle.h5"

    save_comparison_bundle(output_path, bundle)
    loaded = load_comparison_bundle(output_path)

    assert loaded.run_a.sequence_family.value == "FASTSE"
    assert loaded.run_b.run_label == "run_b"
    np.testing.assert_allclose(loaded.run_a.axes["echo_time_s"], run_a.axes["echo_time_s"])
    np.testing.assert_allclose(
        loaded.run_a.observables["echo_signal_abs"],
        run_a.observables["echo_signal_abs"],
    )
    np.testing.assert_allclose(
        loaded.run_a.observables["ft_wh2006_per_echo"],
        run_a.observables["ft_wh2006_per_echo"],
    )
    assert loaded.run_a.scalars["ft_wh2006"] == run_a.scalars["ft_wh2006"]
    assert loaded.run_a.scalars["te_contrast_wh_ms"] == run_a.scalars["te_contrast_wh_ms"]
    assert loaded.run_a.scalars["te_contrast_ms"] == run_a.scalars["te_contrast_ms"]
    assert loaded.derived_ratios["echo_peak_ratio_b_over_a"] == 1.0


def test_comparison_bundle_round_trip_preserves_vfa_fse_runs(tmp_path: Path) -> None:
    family_config = VFAFSEFamilyConfig(
        case_name="vfa_fse_case",
        description="vfa_fse comparison round-trip",
        alpha_exc_deg=90.0,
        phi_exc_deg=0.0,
        alpha_ref_train_deg=[180.0, 150.0, 120.0, 90.0],
        phi_ref_train_deg=None,
        esp_ms=8.0,
        te_nominal_ms=16.0,
        n_iso=101,
        off_resonance_hz=0.0,
    )
    physics = CommonPhysicsConfig(t1_s=1.2, t2_s=0.08, m0=1.0)
    run_a = run_vfa_fse_simulation(family_config, physics, run_label="run_a")
    run_b = run_vfa_fse_simulation(family_config, physics, run_label="run_b")
    bundle = ComparisonBundle(
        comparison_scope="physics_only",
        comparison_modes=("matched_resolution",),
        run_a=run_a,
        run_b=run_b,
        matched_constraints_summary={"delta_te_center_k_ms": 0.0},
        derived_ratios={"echo_peak_ratio_b_over_a": 1.0},
        report_metadata={"status": "ok"},
    )
    output_path = tmp_path / "vfa_fse_comparison_bundle.h5"

    save_comparison_bundle(output_path, bundle)
    loaded = load_comparison_bundle(output_path)

    assert loaded.run_a.sequence_family.value == "VFA_FSE"
    assert loaded.run_b.run_label == "run_b"
    np.testing.assert_allclose(loaded.run_a.axes["echo_time_s"], run_a.axes["echo_time_s"])
    np.testing.assert_allclose(
        loaded.run_a.observables["flip_train_deg"],
        run_a.observables["flip_train_deg"],
    )
    np.testing.assert_allclose(
        loaded.run_a.observables["te_equiv_busse_ms_per_echo"],
        run_a.observables["te_equiv_busse_ms_per_echo"],
    )
    np.testing.assert_allclose(
        loaded.run_a.observables["ft_wh2006_per_echo"],
        run_a.observables["ft_wh2006_per_echo"],
    )
    assert loaded.run_a.scalars["te_equiv_busse_ms"] == run_a.scalars["te_equiv_busse_ms"]
    assert loaded.run_a.scalars["ft_wh2006"] == run_a.scalars["ft_wh2006"]
    assert loaded.run_a.scalars["te_contrast_wh_ms"] == run_a.scalars["te_contrast_wh_ms"]
    assert loaded.run_a.scalars["te_contrast_ms"] == run_a.scalars["te_contrast_ms"]
    assert loaded.derived_ratios["echo_peak_ratio_b_over_a"] == 1.0


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

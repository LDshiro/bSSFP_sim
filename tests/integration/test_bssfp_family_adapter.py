"""Integration tests for generic bSSFP results written through the legacy adapter."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from bssfpviz.io.hdf5_store import load_dataset
from bssfpviz.models.run_config import RunConfig
from bssfpviz.sequences.bssfp.legacy_io import save_legacy_bssfp_result
from bssfpviz.sequences.bssfp.runner import run_bssfp_simulation


def test_generic_bssfp_result_can_round_trip_through_legacy_hdf5(tmp_path: Path) -> None:
    config_path = tmp_path / "small_compute.yaml"
    output_path = tmp_path / "adapter_round_trip.h5"
    config_path.write_text(_small_config_text(), encoding="utf-8")
    config = RunConfig.from_yaml(config_path)

    result = run_bssfp_simulation(config, run_label="adapter")
    save_legacy_bssfp_result(output_path, config, result)
    loaded = load_dataset(output_path)

    np.testing.assert_allclose(
        loaded.reference_m_xyz,
        np.transpose(result.trajectories["reference_m"], (1, 0, 2, 3)),
    )
    np.testing.assert_allclose(
        loaded.steady_state_orbit_xyz,
        np.transpose(result.trajectories["steady_state_orbit_m"], (1, 0, 2, 3)),
    )
    np.testing.assert_allclose(
        loaded.steady_state_fixed_point_xyz,
        np.transpose(result.observables["fixed_points"], (1, 0, 2)),
    )
    np.testing.assert_allclose(
        loaded.sos_profile_magnitude,
        result.observables["sos_abs"],
    )


def _small_config_text() -> str:
    return """
meta:
  case_name: "adapter_case"
  description: "adapter integration case"

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

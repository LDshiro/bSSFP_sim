"""Unit tests for the idealized manual VFA-FSE runner."""

from __future__ import annotations

import numpy as np
import pytest

from bssfpviz.models.comparison import CommonPhysicsConfig, FastSEFamilyConfig, VFAFSEFamilyConfig
from bssfpviz.sequences.fastse.runner import run_fastse_simulation
from bssfpviz.sequences.vfa_fse.runner import run_vfa_fse_simulation


def test_vfa_fse_runner_matches_fastse_for_constant_180_train() -> None:
    physics = CommonPhysicsConfig(t1_s=1.0e9, t2_s=1.0e9, m0=1.0)
    fastse_result = run_fastse_simulation(
        FastSEFamilyConfig(
            case_name="fastse_180",
            description="conventional baseline",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_const_deg=180.0,
            phi_ref_deg=90.0,
            etl=4,
            esp_ms=8.0,
            te_nominal_ms=16.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        physics,
        run_label="fastse",
    )
    vfa_result = run_vfa_fse_simulation(
        VFAFSEFamilyConfig(
            case_name="vfa_180",
            description="manual train equivalent",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_train_deg=[180.0, 180.0, 180.0, 180.0],
            phi_ref_train_deg=None,
            esp_ms=8.0,
            te_nominal_ms=16.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        physics,
        run_label="vfa",
    )

    np.testing.assert_allclose(
        vfa_result.observables["echo_signal_abs"],
        fastse_result.observables["echo_signal_abs"],
    )
    np.testing.assert_allclose(
        vfa_result.observables["fid_signal_abs"],
        fastse_result.observables["fid_signal_abs"],
    )
    np.testing.assert_allclose(
        vfa_result.trajectories["event_m"],
        fastse_result.trajectories["event_m"],
    )


def test_vfa_fse_runner_matches_fastse_for_constant_120_train() -> None:
    physics = CommonPhysicsConfig(t1_s=1.0e9, t2_s=1.0e9, m0=1.0)
    fastse_result = run_fastse_simulation(
        FastSEFamilyConfig(
            case_name="fastse_120",
            description="low-flip baseline",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_const_deg=120.0,
            phi_ref_deg=90.0,
            etl=4,
            esp_ms=8.0,
            te_nominal_ms=16.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        physics,
        run_label="fastse",
    )
    vfa_result = run_vfa_fse_simulation(
        VFAFSEFamilyConfig(
            case_name="vfa_120",
            description="manual train equivalent",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_train_deg=[120.0, 120.0, 120.0, 120.0],
            phi_ref_train_deg=None,
            esp_ms=8.0,
            te_nominal_ms=16.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        physics,
        run_label="vfa",
    )

    np.testing.assert_allclose(
        vfa_result.observables["echo_signal_abs"],
        fastse_result.observables["echo_signal_abs"],
    )
    np.testing.assert_allclose(
        vfa_result.observables["fid_signal_abs"],
        fastse_result.observables["fid_signal_abs"],
    )
    np.testing.assert_allclose(
        vfa_result.trajectories["event_m"],
        fastse_result.trajectories["event_m"],
    )


def test_vfa_fse_runner_preserves_variable_train_and_nonzero_fid() -> None:
    result = run_vfa_fse_simulation(
        VFAFSEFamilyConfig(
            case_name="vfa_manual",
            description="manual variable train",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_train_deg=[180.0, 150.0, 120.0, 90.0],
            phi_ref_train_deg=[90.0, 100.0, 110.0, 120.0],
            esp_ms=8.0,
            te_nominal_ms=16.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        CommonPhysicsConfig(t1_s=1.0e9, t2_s=1.0e9, m0=1.0),
        run_label="vfa",
    )

    flip_train_deg = np.asarray(result.observables["flip_train_deg"], dtype=np.float64)
    fid_signal_abs = np.asarray(result.observables["fid_signal_abs"], dtype=np.float64)

    np.testing.assert_allclose(
        flip_train_deg,
        np.array([90.0, 180.0, 150.0, 120.0, 90.0], dtype=np.float64),
    )
    assert fid_signal_abs.shape == (4,)
    assert float(np.max(fid_signal_abs)) > 0.0


def test_vfa_fse_runner_generates_finite_nonnegative_busse_te_per_echo() -> None:
    result = run_vfa_fse_simulation(
        VFAFSEFamilyConfig(
            case_name="vfa_busse",
            description="manual variable train",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_train_deg=[180.0, 150.0, 120.0, 90.0],
            phi_ref_train_deg=[90.0, 100.0, 110.0, 120.0],
            esp_ms=8.0,
            te_nominal_ms=16.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        CommonPhysicsConfig(t1_s=1.2, t2_s=0.08, m0=1.0),
        run_label="vfa",
    )

    te_equiv_busse_ms_per_echo = np.asarray(
        result.observables["te_equiv_busse_ms_per_echo"],
        dtype=np.float64,
    )

    assert te_equiv_busse_ms_per_echo.shape == (4,)
    assert np.all(np.isfinite(te_equiv_busse_ms_per_echo))
    assert np.all(te_equiv_busse_ms_per_echo >= 0.0)
    assert float(result.scalars["te_equiv_busse_ms"]) >= 0.0
    ft_wh2006_per_echo = np.asarray(result.observables["ft_wh2006_per_echo"], dtype=np.float64)
    te_contrast_wh_ms_per_echo = np.asarray(
        result.observables["te_contrast_wh_ms_per_echo"],
        dtype=np.float64,
    )
    assert ft_wh2006_per_echo.shape == (4,)
    assert te_contrast_wh_ms_per_echo.shape == (4,)
    assert np.all(np.isfinite(ft_wh2006_per_echo))
    assert np.all(np.isfinite(te_contrast_wh_ms_per_echo))
    assert np.all(ft_wh2006_per_echo >= 0.0)
    assert float(result.scalars["te_contrast_ms"]) == float(result.scalars["te_equiv_busse_ms"])
    assert float(result.scalars["te_contrast_wh_ms"]) >= 0.0
    assert result.family_metadata["te_contrast_definition"] == "Busse"


def test_vfa_fse_runner_returns_zero_busse_te_for_no_relaxation_case() -> None:
    result = run_vfa_fse_simulation(
        VFAFSEFamilyConfig(
            case_name="vfa_no_relax",
            description="manual train no relaxation",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_train_deg=[180.0, 150.0, 120.0, 90.0],
            phi_ref_train_deg=None,
            esp_ms=8.0,
            te_nominal_ms=16.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        CommonPhysicsConfig(t1_s=float("inf"), t2_s=float("inf"), m0=1.0),
        run_label="vfa",
    )

    te_equiv_busse_ms_per_echo = np.asarray(
        result.observables["te_equiv_busse_ms_per_echo"],
        dtype=np.float64,
    )

    np.testing.assert_allclose(te_equiv_busse_ms_per_echo, np.zeros(4, dtype=np.float64))
    assert float(result.scalars["te_equiv_busse_ms"]) == 0.0
    assert np.isnan(float(result.scalars["ft_wh2006"]))
    assert np.isnan(float(result.scalars["te_contrast_wh_ms"]))
    assert result.family_metadata["contrast_warnings"] == [
        "WH2006 contrast metrics are unavailable because T1 and T2 are indistinguishable."
    ]


def test_vfa_fse_runner_constant_180_train_has_busse_te_close_to_center_te() -> None:
    result = run_vfa_fse_simulation(
        VFAFSEFamilyConfig(
            case_name="vfa_center_te",
            description="conventional train",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_train_deg=[180.0, 180.0, 180.0, 180.0],
            phi_ref_train_deg=None,
            esp_ms=8.0,
            te_nominal_ms=16.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        CommonPhysicsConfig(t1_s=1.2, t2_s=0.08, m0=1.0),
        run_label="vfa",
    )

    te_center_k_ms = float(result.scalars["te_center_k_ms"])
    te_equiv_busse_ms = float(result.scalars["te_equiv_busse_ms"])

    assert te_equiv_busse_ms == pytest.approx(te_center_k_ms, abs=1.0e-3)

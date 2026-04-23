"""Unit tests for the idealized FASTSE baseline runner."""

from __future__ import annotations

import numpy as np
import pytest

from bssfpviz.models.comparison import CommonPhysicsConfig, FastSEFamilyConfig
from bssfpviz.sequences.fastse.runner import run_fastse_simulation


def test_fastse_runner_matches_w2014_cpmg120_no_relax_reference() -> None:
    result = run_fastse_simulation(
        FastSEFamilyConfig(
            case_name="w2014_cpmg120",
            description="validation case",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_const_deg=120.0,
            phi_ref_deg=90.0,
            etl=3,
            esp_ms=8.0,
            te_nominal_ms=16.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        CommonPhysicsConfig(t1_s=1.0e9, t2_s=1.0e9, m0=1.0),
        run_label="fastse",
    )

    echo_signal_abs = np.asarray(result.observables["echo_signal_abs"], dtype=np.float64)
    np.testing.assert_allclose(
        echo_signal_abs,
        np.array([0.75, 0.9375, 0.84375], dtype=np.float64),
        atol=2.5e-2,
        rtol=0.0,
    )


def test_fastse_runner_generates_fid_samples_for_120_degree_case() -> None:
    result = run_fastse_simulation(
        FastSEFamilyConfig(
            case_name="fastse_fid",
            description="fid validation",
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
        CommonPhysicsConfig(t1_s=1.0e9, t2_s=1.0e9, m0=1.0),
        run_label="fastse",
    )

    fid_signal_abs = np.asarray(result.observables["fid_signal_abs"], dtype=np.float64)
    assert fid_signal_abs.shape == (4,)
    assert float(np.max(fid_signal_abs)) > 0.0


def test_fastse_runner_conventional_180_degree_fid_peak_is_below_echo_peak() -> None:
    result = run_fastse_simulation(
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
        CommonPhysicsConfig(t1_s=1.0e9, t2_s=1.0e9, m0=1.0),
        run_label="fastse",
    )

    fid_peak_abs = float(result.scalars["fid_peak_abs"])
    echo_peak_abs = float(result.scalars["echo_peak_abs"])
    assert fid_peak_abs < echo_peak_abs


def test_fastse_runner_conventional_180_degree_has_wh2006_metrics_equal_to_center_te() -> None:
    result = run_fastse_simulation(
        FastSEFamilyConfig(
            case_name="fastse_180_wh",
            description="conventional baseline",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_const_deg=180.0,
            phi_ref_deg=90.0,
            etl=19,
            esp_ms=8.0,
            te_nominal_ms=80.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        CommonPhysicsConfig(t1_s=1.2, t2_s=0.08, m0=1.0),
        run_label="fastse",
    )

    assert float(result.scalars["ft_wh2006"]) == pytest.approx(1.0, abs=1.0e-2)
    assert float(result.scalars["te_contrast_wh_ms"]) == pytest.approx(
        float(result.scalars["te_center_k_ms"]),
        abs=1.0e-2,
    )
    assert float(result.scalars["te_contrast_ms"]) == pytest.approx(
        float(result.scalars["te_center_k_ms"]),
        abs=1.0e-8,
    )
    assert result.family_metadata["te_contrast_definition"] == "TE_center-k"


@pytest.mark.parametrize(
    ("alpha_ref_const_deg", "expected_ft"),
    [
        (150.0, 0.963),
        (120.0, 0.877),
        (90.0, 0.739),
        (60.0, 0.573),
    ],
)
def test_fastse_runner_reproduces_wh2006_low_flip_ft_reference(
    alpha_ref_const_deg: float,
    expected_ft: float,
) -> None:
    result = run_fastse_simulation(
        FastSEFamilyConfig(
            case_name=f"fastse_{int(alpha_ref_const_deg)}",
            description="wh2006 validation",
            alpha_exc_deg=90.0,
            phi_exc_deg=0.0,
            alpha_ref_const_deg=alpha_ref_const_deg,
            phi_ref_deg=90.0,
            etl=19,
            esp_ms=8.0,
            te_nominal_ms=80.0,
            n_iso=1001,
            off_resonance_hz=0.0,
        ),
        CommonPhysicsConfig(t1_s=1.0, t2_s=0.08, m0=1.0),
        run_label="fastse",
    )

    assert float(result.scalars["ft_wh2006"]) == pytest.approx(expected_ft, abs=6.0e-2)
    assert float(result.scalars["te_contrast_ms"]) == pytest.approx(
        float(result.scalars["te_contrast_wh_ms"]),
        abs=1.0e-8,
    )
    assert result.family_metadata["te_contrast_definition"] == "WH2006"

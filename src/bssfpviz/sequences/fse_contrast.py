"""Contrast-metric helpers shared by train-based FSE family runners."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from bssfpviz.models.comparison import CommonPhysicsConfig, SequenceFamily, SimulationResult
from bssfpviz.sequences.fse_common import run_train_based_fse_simulation

FloatArray = npt.NDArray[np.float64]


@dataclass(slots=True, frozen=True)
class WH2006ContrastMetrics:
    """Derived WH2006 contrast outputs for one echo train."""

    ft_per_echo: FloatArray
    te_contrast_wh_ms_per_echo: FloatArray
    ft_center_k: float
    te_contrast_wh_ms: float
    warnings: tuple[str, ...]


def run_no_relaxation_reference(
    *,
    sequence_family: SequenceFamily,
    run_label: str,
    case_name: str,
    description: str,
    physics: CommonPhysicsConfig,
    alpha_exc_deg: float,
    phi_exc_deg: float,
    alpha_ref_train_deg: npt.ArrayLike,
    phi_ref_train_deg: npt.ArrayLike,
    esp_ms: float,
    n_iso: int,
    off_resonance_hz: float,
    metadata: dict[str, str] | None = None,
    family_metadata: dict[str, Any] | None = None,
) -> SimulationResult:
    """Run the shared no-relaxation reference used by FSE contrast metrics."""
    no_relaxation_physics = CommonPhysicsConfig(
        t1_s=float("inf"),
        t2_s=float("inf"),
        m0=physics.m0,
    )
    return run_train_based_fse_simulation(
        sequence_family=sequence_family,
        run_label=f"{run_label}_no_relax",
        case_name=case_name,
        description=description,
        physics=no_relaxation_physics,
        alpha_exc_deg=alpha_exc_deg,
        phi_exc_deg=phi_exc_deg,
        alpha_ref_train_deg=alpha_ref_train_deg,
        phi_ref_train_deg=phi_ref_train_deg,
        esp_ms=esp_ms,
        n_iso=n_iso,
        off_resonance_hz=off_resonance_hz,
        metadata=metadata,
        family_metadata=family_metadata,
    )


def compute_busse_te_ms_per_echo(
    result: SimulationResult,
    no_relaxation_result: SimulationResult,
    *,
    t2_s: float,
) -> FloatArray:
    """Return Busse contrast-equivalent TE per echo in milliseconds."""
    echo_signal_abs = np.asarray(result.observables["echo_signal_abs"], dtype=np.float64)
    coherence_abs = np.asarray(
        no_relaxation_result.observables["echo_signal_abs"],
        dtype=np.float64,
    )
    if not np.isfinite(t2_s):
        return np.zeros_like(echo_signal_abs, dtype=np.float64)
    relaxation_factor = _relaxation_factor(
        signal_abs=echo_signal_abs,
        coherence_abs=coherence_abs,
    )
    return np.asarray((-float(t2_s) * np.log(relaxation_factor)) * 1.0e3, dtype=np.float64)


def compute_wh2006_metrics(
    result: SimulationResult,
    no_relaxation_result: SimulationResult,
    *,
    physics: CommonPhysicsConfig,
) -> WH2006ContrastMetrics:
    """Return WH2006 f_t and TE_contrast metrics derived from echo amplitudes."""
    echo_signal_abs = np.asarray(result.observables["echo_signal_abs"], dtype=np.float64)
    coherence_abs = np.asarray(
        no_relaxation_result.observables["echo_signal_abs"],
        dtype=np.float64,
    )
    echo_time_s = np.asarray(result.axes["echo_time_s"], dtype=np.float64)
    center_echo_index = int(echo_time_s.shape[0] // 2)
    warnings: list[str] = []

    inverse_t1 = _safe_inverse(physics.t1_s)
    inverse_t2 = _safe_inverse(physics.t2_s)
    denominator = inverse_t2 - inverse_t1
    if abs(denominator) <= np.finfo(np.float64).eps:
        warnings.append(
            "WH2006 contrast metrics are unavailable because T1 and T2 are indistinguishable."
        )
        nan_array = np.full(echo_time_s.shape, np.nan, dtype=np.float64)
        return WH2006ContrastMetrics(
            ft_per_echo=nan_array,
            te_contrast_wh_ms_per_echo=nan_array.copy(),
            ft_center_k=float("nan"),
            te_contrast_wh_ms=float("nan"),
            warnings=tuple(warnings),
        )

    relaxation_factor = _relaxation_factor(
        signal_abs=echo_signal_abs,
        coherence_abs=coherence_abs,
    )
    decay_rate = -np.log(relaxation_factor) / np.maximum(
        echo_time_s,
        np.finfo(np.float64).tiny,
    )
    ft_per_echo = np.clip((decay_rate - inverse_t1) / denominator, 0.0, 1.0)
    te_contrast_wh_ms_per_echo = np.asarray(ft_per_echo * echo_time_s * 1.0e3, dtype=np.float64)
    return WH2006ContrastMetrics(
        ft_per_echo=np.asarray(ft_per_echo, dtype=np.float64),
        te_contrast_wh_ms_per_echo=te_contrast_wh_ms_per_echo,
        ft_center_k=float(ft_per_echo[center_echo_index]),
        te_contrast_wh_ms=float(te_contrast_wh_ms_per_echo[center_echo_index]),
        warnings=tuple(warnings),
    )


def _relaxation_factor(
    *,
    signal_abs: FloatArray,
    coherence_abs: FloatArray,
) -> FloatArray:
    safe_denominator = np.maximum(coherence_abs, np.finfo(np.float64).tiny)
    ratio = np.divide(
        signal_abs,
        safe_denominator,
        out=np.zeros_like(signal_abs, dtype=np.float64),
        where=safe_denominator > 0.0,
    )
    return np.clip(ratio, np.finfo(np.float64).tiny, 1.0)


def _safe_inverse(value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return 1.0 / float(value)

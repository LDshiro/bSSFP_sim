"""Helpers for the idealized FASTSE baseline family."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from bssfpviz.models.comparison import FastSEFamilyConfig

FloatArray = npt.NDArray[np.float64]


def build_iso_positions(n_iso: int) -> FloatArray:
    """Return the effective-1D isochromat positions on [-0.5, 0.5)."""
    return np.asarray(np.linspace(-0.5, 0.5, int(n_iso), endpoint=False), dtype=np.float64)


def build_echo_time_s(config: FastSEFamilyConfig) -> FloatArray:
    """Return echo-center sampling times for one echo train."""
    esp_s = float(config.esp_ms) * 1.0e-3
    return np.asarray((1.0 + np.arange(config.etl, dtype=np.float64)) * esp_s, dtype=np.float64)


def build_fid_time_s(config: FastSEFamilyConfig) -> FloatArray:
    """Return FID sampling times immediately after refocusing pulses."""
    esp_s = float(config.esp_ms) * 1.0e-3
    return np.asarray((0.5 + np.arange(config.etl, dtype=np.float64)) * esp_s, dtype=np.float64)


def build_event_time_s(config: FastSEFamilyConfig) -> FloatArray:
    """Return [excitation, fid_1, echo_1, ..., fid_ETL, echo_ETL] event times."""
    fid_time_s = build_fid_time_s(config)
    echo_time_s = build_echo_time_s(config)
    event_times = [0.0]
    for echo_index in range(config.etl):
        event_times.append(float(fid_time_s[echo_index]))
        event_times.append(float(echo_time_s[echo_index]))
    return np.asarray(event_times, dtype=np.float64)


def build_flip_train_deg(config: FastSEFamilyConfig) -> FloatArray:
    """Return [alpha_exc, alpha_ref_1, ..., alpha_ref_ETL]."""
    return np.asarray(
        [config.alpha_exc_deg, *([config.alpha_ref_const_deg] * config.etl)],
        dtype=np.float64,
    )


def build_phase_train_deg(config: FastSEFamilyConfig) -> FloatArray:
    """Return [phi_exc, phi_ref_1, ..., phi_ref_ETL]."""
    return np.asarray(
        [config.phi_exc_deg, *([config.phi_ref_deg] * config.etl)],
        dtype=np.float64,
    )


def compute_te_center_k_ms(config: FastSEFamilyConfig) -> float:
    """Return the center-k echo time using the middle echo of the train."""
    echo_time_s = build_echo_time_s(config)
    center_echo_index = int(config.etl // 2)
    return float(echo_time_s[center_echo_index] * 1.0e3)

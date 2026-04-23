"""Shared helpers for train-based FSE family simulations."""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

from bssfpviz.core.propagators import segment_affine_propagator
from bssfpviz.core.rf import hard_pulse_rotation
from bssfpviz.models.comparison import CommonPhysicsConfig, SequenceFamily, SimulationResult
from bssfpviz.models.config import PhysicsConfig as CorePhysicsConfig

ComplexArray = npt.NDArray[np.complex128]
FloatArray = npt.NDArray[np.float64]


def build_iso_positions(n_iso: int) -> FloatArray:
    """Return the effective-1D isochromat positions on [-0.5, 0.5)."""
    return np.asarray(np.linspace(-0.5, 0.5, int(n_iso), endpoint=False), dtype=np.float64)


def build_echo_time_s(*, etl: int, esp_ms: float) -> FloatArray:
    """Return echo-center sampling times for one echo train."""
    esp_s = float(esp_ms) * 1.0e-3
    return np.asarray((1.0 + np.arange(int(etl), dtype=np.float64)) * esp_s, dtype=np.float64)


def build_fid_time_s(*, etl: int, esp_ms: float) -> FloatArray:
    """Return FID sampling times immediately after refocusing pulses."""
    esp_s = float(esp_ms) * 1.0e-3
    return np.asarray((0.5 + np.arange(int(etl), dtype=np.float64)) * esp_s, dtype=np.float64)


def build_event_time_s(*, etl: int, esp_ms: float) -> FloatArray:
    """Return [excitation, fid_1, echo_1, ..., fid_ETL, echo_ETL] event times."""
    fid_time_s = build_fid_time_s(etl=etl, esp_ms=esp_ms)
    echo_time_s = build_echo_time_s(etl=etl, esp_ms=esp_ms)
    event_times = [0.0]
    for echo_index in range(int(etl)):
        event_times.append(float(fid_time_s[echo_index]))
        event_times.append(float(echo_time_s[echo_index]))
    return np.asarray(event_times, dtype=np.float64)


def compute_te_center_k_ms(*, etl: int, esp_ms: float) -> float:
    """Return the center-k echo time using the middle echo of the train."""
    echo_time_s = build_echo_time_s(etl=etl, esp_ms=esp_ms)
    center_echo_index = int(etl // 2)
    return float(echo_time_s[center_echo_index] * 1.0e3)


def build_flip_train_deg(
    *,
    alpha_exc_deg: float,
    alpha_ref_train_deg: npt.ArrayLike,
) -> FloatArray:
    """Return [alpha_exc, alpha_ref_1, ..., alpha_ref_ETL]."""
    alpha_ref_train = _as_train_array(alpha_ref_train_deg, name="alpha_ref_train_deg")
    return np.asarray([float(alpha_exc_deg), *alpha_ref_train.tolist()], dtype=np.float64)


def build_phase_train_deg(
    *,
    phi_exc_deg: float,
    phi_ref_train_deg: npt.ArrayLike,
) -> FloatArray:
    """Return [phi_exc, phi_ref_1, ..., phi_ref_ETL]."""
    phi_ref_train = _as_train_array(phi_ref_train_deg, name="phi_ref_train_deg")
    return np.asarray([float(phi_exc_deg), *phi_ref_train.tolist()], dtype=np.float64)


def run_train_based_fse_simulation(
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
    """Run one idealized train-based FSE simulation and return a generic result."""
    alpha_ref_train = _as_train_array(alpha_ref_train_deg, name="alpha_ref_train_deg")
    phi_ref_train = _as_train_array(phi_ref_train_deg, name="phi_ref_train_deg")
    if alpha_ref_train.shape != phi_ref_train.shape:
        msg = "alpha_ref_train_deg and phi_ref_train_deg must have the same shape."
        raise ValueError(msg)

    etl = int(alpha_ref_train.shape[0])
    iso_positions = build_iso_positions(n_iso)
    echo_time_s = build_echo_time_s(etl=etl, esp_ms=esp_ms)
    fid_time_s = build_fid_time_s(etl=etl, esp_ms=esp_ms)
    event_time_s = build_event_time_s(etl=etl, esp_ms=esp_ms)
    flip_train_deg = build_flip_train_deg(
        alpha_exc_deg=alpha_exc_deg,
        alpha_ref_train_deg=alpha_ref_train,
    )
    phase_train_deg = build_phase_train_deg(
        phi_exc_deg=phi_exc_deg,
        phi_ref_train_deg=phi_ref_train,
    )

    core_physics = CorePhysicsConfig(t1_s=physics.t1_s, t2_s=physics.t2_s, m0=physics.m0)
    excitation_rotation = hard_pulse_rotation(np.deg2rad(alpha_exc_deg), np.deg2rad(phi_exc_deg))
    half_echo_s = float(esp_ms) * 0.5e-3
    free_propagators = _build_half_echo_propagators(
        iso_positions=iso_positions,
        off_resonance_hz=off_resonance_hz,
        half_echo_s=half_echo_s,
        physics=core_physics,
    )

    magnetization = np.zeros((int(n_iso), 3), dtype=np.float64)
    magnetization[:, 2] = float(physics.m0)
    magnetization = _apply_rotation(magnetization, excitation_rotation)

    event_states = [np.asarray(magnetization, dtype=np.float64)]
    echo_signal_complex = np.zeros(etl, dtype=np.complex128)
    fid_signal_complex = np.zeros(etl, dtype=np.complex128)

    for echo_index, (alpha_ref_deg, phi_ref_deg) in enumerate(
        zip(alpha_ref_train, phi_ref_train, strict=True)
    ):
        magnetization = _apply_free_evolution(magnetization, free_propagators)
        refocusing_rotation = hard_pulse_rotation(
            np.deg2rad(float(alpha_ref_deg)),
            np.deg2rad(float(phi_ref_deg)),
        )
        magnetization = _apply_rotation(magnetization, refocusing_rotation)
        fid_signal_complex[echo_index] = _ensemble_signal(magnetization)
        event_states.append(np.asarray(magnetization, dtype=np.float64))

        magnetization = _apply_free_evolution(magnetization, free_propagators)
        echo_signal_complex[echo_index] = _ensemble_signal(magnetization)
        event_states.append(np.asarray(magnetization, dtype=np.float64))

    event_m = np.asarray(event_states, dtype=np.float64)
    echo_signal_abs = np.abs(echo_signal_complex)
    fid_signal_abs = np.abs(fid_signal_complex)

    return SimulationResult(
        sequence_family=sequence_family,
        run_label=run_label,
        case_name=case_name,
        description=description,
        metadata={
            "runner": "train_based_fse_runner",
            "comparison_ready": "true",
            **(metadata or {}),
        },
        family_metadata={
            "sampling": "echo_plus_fid",
            **(family_metadata or {}),
        },
        axes={
            "event_time_s": event_time_s,
            "echo_time_s": echo_time_s,
            "fid_time_s": fid_time_s,
            "iso_position": iso_positions,
        },
        trajectories={
            "event_m": event_m,
        },
        observables={
            "echo_signal_complex": np.asarray(echo_signal_complex, dtype=np.complex128),
            "echo_signal_abs": np.asarray(echo_signal_abs, dtype=np.float64),
            "fid_signal_complex": np.asarray(fid_signal_complex, dtype=np.complex128),
            "fid_signal_abs": np.asarray(fid_signal_abs, dtype=np.float64),
            "flip_train_deg": flip_train_deg,
            "phase_train_deg": phase_train_deg,
        },
        scalars={
            "etl": etl,
            "n_iso": int(n_iso),
            "esp_ms": float(esp_ms),
            "te_center_k_ms": compute_te_center_k_ms(etl=etl, esp_ms=esp_ms),
            "echo_peak_abs": float(np.max(echo_signal_abs)),
            "fid_peak_abs": float(np.max(fid_signal_abs)),
        },
    )


def _as_train_array(value: npt.ArrayLike, *, name: str) -> FloatArray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 1 or array.shape[0] == 0:
        msg = f"{name} must be a non-empty 1D float array."
        raise ValueError(msg)
    return np.asarray(array, dtype=np.float64)


def _build_half_echo_propagators(
    *,
    iso_positions: FloatArray,
    off_resonance_hz: float,
    half_echo_s: float,
    physics: CorePhysicsConfig,
) -> list[tuple[FloatArray, FloatArray]]:
    gradient_phase_rad = np.pi * np.asarray(iso_positions, dtype=np.float64)
    off_resonance_rad_s = float(2.0 * np.pi * off_resonance_hz)
    propagators: list[tuple[FloatArray, FloatArray]] = []
    for phase_rad in gradient_phase_rad:
        total_delta_omega_rad_s = off_resonance_rad_s + float(phase_rad) / half_echo_s
        phi3, c3, _ = segment_affine_propagator(
            ux=0.0,
            uy=0.0,
            delta_omega_rad_s=total_delta_omega_rad_s,
            dt_s=half_echo_s,
            physics=physics,
        )
        propagators.append((phi3, c3))
    return propagators


def _apply_rotation(magnetization: FloatArray, rotation: FloatArray) -> FloatArray:
    return np.asarray((rotation @ magnetization.T).T, dtype=np.float64)


def _apply_free_evolution(
    magnetization: FloatArray,
    propagators: list[tuple[FloatArray, FloatArray]],
) -> FloatArray:
    updated = np.empty_like(magnetization)
    for iso_index, (phi3, c3) in enumerate(propagators):
        updated[iso_index] = phi3 @ magnetization[iso_index] + c3
    return updated


def _ensemble_signal(magnetization: FloatArray) -> complex:
    transverse = np.asarray(magnetization[:, 0] + 1j * magnetization[:, 1], dtype=np.complex128)
    return complex(np.mean(transverse))

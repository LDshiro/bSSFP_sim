"""Idealized FASTSE family runner for the comparison backend."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from bssfpviz.core.propagators import segment_affine_propagator
from bssfpviz.core.rf import hard_pulse_rotation
from bssfpviz.models.comparison import (
    CommonPhysicsConfig,
    FastSEFamilyConfig,
    SequenceFamily,
    SimulationResult,
)
from bssfpviz.models.config import PhysicsConfig as CorePhysicsConfig
from bssfpviz.sequences.fastse.sequence import (
    build_echo_time_s,
    build_event_time_s,
    build_fid_time_s,
    build_flip_train_deg,
    build_iso_positions,
    build_phase_train_deg,
    compute_te_center_k_ms,
)

ComplexArray = npt.NDArray[np.complex128]
FloatArray = npt.NDArray[np.float64]


def run_fastse_simulation(
    config: FastSEFamilyConfig,
    physics: CommonPhysicsConfig,
    *,
    run_label: str = "fastse",
) -> SimulationResult:
    """Run the idealized hard-pulse FASTSE baseline and return a generic result."""
    core_physics = CorePhysicsConfig(t1_s=physics.t1_s, t2_s=physics.t2_s, m0=physics.m0)
    iso_positions = build_iso_positions(config.n_iso)
    echo_time_s = build_echo_time_s(config)
    fid_time_s = build_fid_time_s(config)
    event_time_s = build_event_time_s(config)
    flip_train_deg = build_flip_train_deg(config)
    phase_train_deg = build_phase_train_deg(config)

    excitation_rotation = hard_pulse_rotation(
        np.deg2rad(config.alpha_exc_deg),
        np.deg2rad(config.phi_exc_deg),
    )
    refocusing_rotation = hard_pulse_rotation(
        np.deg2rad(config.alpha_ref_const_deg),
        np.deg2rad(config.phi_ref_deg),
    )
    half_echo_s = float(config.esp_ms) * 0.5e-3
    free_propagators = _build_half_echo_propagators(
        iso_positions=iso_positions,
        off_resonance_hz=config.off_resonance_hz,
        half_echo_s=half_echo_s,
        physics=core_physics,
    )

    magnetization = np.zeros((config.n_iso, 3), dtype=np.float64)
    magnetization[:, 2] = float(physics.m0)
    magnetization = _apply_rotation(magnetization, excitation_rotation)

    event_states = [np.asarray(magnetization, dtype=np.float64)]
    echo_signal_complex = np.zeros(config.etl, dtype=np.complex128)
    fid_signal_complex = np.zeros(config.etl, dtype=np.complex128)

    for echo_index in range(config.etl):
        magnetization = _apply_free_evolution(magnetization, free_propagators)
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
        sequence_family=SequenceFamily.FASTSE,
        run_label=run_label,
        case_name=config.case_name,
        description=config.description,
        metadata={
            "runner": "fastse_family_runner",
            "comparison_ready": "true",
        },
        family_metadata={
            "sequence_variant": config.sequence_variant,
            "sampling": "echo_plus_fid",
            "phase_convention": "CPMG",
            "timing_mode": config.timing_mode,
            "initial_state_mode": config.initial_state_mode,
            "dephasing_model": config.dephasing_model,
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
            "etl": config.etl,
            "n_iso": config.n_iso,
            "esp_ms": config.esp_ms,
            "te_center_k_ms": compute_te_center_k_ms(config),
            "echo_peak_abs": float(np.max(echo_signal_abs)),
            "fid_peak_abs": float(np.max(fid_signal_abs)),
        },
    )


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

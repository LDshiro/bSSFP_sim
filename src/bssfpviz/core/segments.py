"""Waveform materialization and 2TR segment construction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from bssfpviz.models.config import SequenceConfig, SimulationConfig

FloatArray = npt.NDArray[np.float64]


@dataclass(slots=True)
class SegmentSequence:
    """Piecewise-constant controls for one 2TR superperiod.

    Shapes:
    - `segment_dt_s`: `(n_segments,)`
    - `segment_ux`: `(n_segments,)`
    - `segment_uy`: `(n_segments,)`
    - `boundary_time_s`: `(n_segments + 1,)`
    """

    segment_dt_s: FloatArray
    segment_ux: FloatArray
    segment_uy: FloatArray
    boundary_time_s: FloatArray
    readout_time_s: float

    def __post_init__(self) -> None:
        self.segment_dt_s = np.asarray(self.segment_dt_s, dtype=np.float64)
        self.segment_ux = np.asarray(self.segment_ux, dtype=np.float64)
        self.segment_uy = np.asarray(self.segment_uy, dtype=np.float64)
        self.boundary_time_s = np.asarray(self.boundary_time_s, dtype=np.float64)
        if not (self.segment_dt_s.ndim == self.segment_ux.ndim == self.segment_uy.ndim == 1):
            msg = "Segment arrays must be 1D."
            raise ValueError(msg)
        if not (self.segment_dt_s.shape == self.segment_ux.shape == self.segment_uy.shape):
            msg = "segment_dt_s, segment_ux, and segment_uy must have the same shape."
            raise ValueError(msg)
        if self.boundary_time_s.shape != (self.segment_dt_s.shape[0] + 1,):
            msg = "boundary_time_s must have one more element than the segment arrays."
            raise ValueError(msg)


def make_base_rf_waveform(sequence_config: SequenceConfig) -> FloatArray:
    """Return the shared base RF waveform with shape `(n_rf_samples, 2)`."""
    n_rf_samples = sequence_config.n_rf_samples
    dt_rf = sequence_config.rf_duration_s / n_rf_samples
    envelope = np.hanning(n_rf_samples + 2)[1:-1]
    ux_scale = sequence_config.flip_angle_rad / (np.sum(envelope) * dt_rf)
    rf_xy = np.zeros((n_rf_samples, 2), dtype=np.float64)
    rf_xy[:, 0] = envelope * ux_scale
    return rf_xy


def materialize_actual_waveforms(
    base_rf_xy: FloatArray, phase_schedule_rad: FloatArray
) -> FloatArray:
    """Rotate one shared base waveform into actual acquisition/pulse waveforms."""
    base_rf_xy = np.asarray(base_rf_xy, dtype=np.float64)
    phase_schedule_rad = np.asarray(phase_schedule_rad, dtype=np.float64)
    if base_rf_xy.ndim != 2 or base_rf_xy.shape[1] != 2:
        msg = "base_rf_xy must have shape (n_rf_samples, 2)."
        raise ValueError(msg)
    if phase_schedule_rad.ndim != 2 or phase_schedule_rad.shape[1] != 2:
        msg = "phase_schedule_rad must have shape (n_acq, 2)."
        raise ValueError(msg)

    ux_base = base_rf_xy[:, 0]
    uy_base = base_rf_xy[:, 1]
    cos_phi = np.cos(phase_schedule_rad)[:, :, None]
    sin_phi = np.sin(phase_schedule_rad)[:, :, None]

    actual_rf_xy = np.zeros(
        (phase_schedule_rad.shape[0], 2, base_rf_xy.shape[0], 2), dtype=np.float64
    )
    actual_rf_xy[:, :, :, 0] = cos_phi * ux_base[None, None, :] - sin_phi * uy_base[None, None, :]
    actual_rf_xy[:, :, :, 1] = sin_phi * ux_base[None, None, :] + cos_phi * uy_base[None, None, :]
    return actual_rf_xy


def build_superperiod_segments(
    actual_rf_xy: FloatArray, delta_omega_rad_s: float, config: SimulationConfig
) -> SegmentSequence:
    """Build the explicit 2TR segment sequence for one acquisition."""
    del delta_omega_rad_s

    actual_rf_xy = np.asarray(actual_rf_xy, dtype=np.float64)
    if actual_rf_xy.shape != (2, config.sequence.n_rf_samples, 2):
        msg = (
            "actual_rf_xy must have shape "
            f"(2, {config.sequence.n_rf_samples}, 2) for one acquisition."
        )
        raise ValueError(msg)

    n_rf_samples = config.sequence.n_rf_samples
    dt_rf = config.sequence.rf_duration_s / n_rf_samples

    segment_dt_s = np.concatenate(
        [
            np.full(n_rf_samples, dt_rf, dtype=np.float64),
            np.array([config.sequence.free_duration_s], dtype=np.float64),
            np.full(n_rf_samples, dt_rf, dtype=np.float64),
            np.array([config.sequence.free_duration_s], dtype=np.float64),
        ]
    )
    segment_ux = np.concatenate(
        [
            actual_rf_xy[0, :, 0],
            np.array([0.0], dtype=np.float64),
            actual_rf_xy[1, :, 0],
            np.array([0.0], dtype=np.float64),
        ]
    )
    segment_uy = np.concatenate(
        [
            actual_rf_xy[0, :, 1],
            np.array([0.0], dtype=np.float64),
            actual_rf_xy[1, :, 1],
            np.array([0.0], dtype=np.float64),
        ]
    )
    boundary_time_s = np.concatenate(
        [np.array([0.0], dtype=np.float64), np.cumsum(segment_dt_s, dtype=np.float64)]
    )
    readout_time_s = config.sequence.rf_duration_s + 0.5 * config.sequence.free_duration_s

    return SegmentSequence(
        segment_dt_s=segment_dt_s,
        segment_ux=segment_ux,
        segment_uy=segment_uy,
        boundary_time_s=boundary_time_s,
        readout_time_s=readout_time_s,
    )

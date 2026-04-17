"""Segment-wise affine propagators for the Chapter 3 Bloch model."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
from scipy.linalg import expm

from bssfpviz.core.bloch import augmented_generator
from bssfpviz.models.config import PhysicsConfig

FloatArray = npt.NDArray[np.float64]


def segment_affine_propagator(
    ux: float,
    uy: float,
    delta_omega_rad_s: float,
    dt_s: float,
    physics: PhysicsConfig,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Return the exact affine propagator for one piecewise-constant segment."""
    generator = augmented_generator(ux, uy, delta_omega_rad_s, physics)
    affine4 = np.asarray(expm(generator * dt_s), dtype=np.float64)
    affine3 = np.asarray(affine4[:3, :3], dtype=np.float64)
    offset3 = np.asarray(affine4[:3, 3], dtype=np.float64)
    return affine3, offset3, affine4


def compose_affine_sequence(
    segment_dt_s: FloatArray,
    segment_ux: FloatArray,
    segment_uy: FloatArray,
    delta_omega_rad_s: float,
    physics: PhysicsConfig,
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Compose the affine maps for one 2TR segment sequence."""
    if segment_dt_s.ndim != 1 or segment_ux.ndim != 1 or segment_uy.ndim != 1:
        msg = "segment_dt_s, segment_ux, and segment_uy must be 1D arrays."
        raise ValueError(msg)
    if not (segment_dt_s.shape == segment_ux.shape == segment_uy.shape):
        msg = "segment_dt_s, segment_ux, and segment_uy must have the same shape."
        raise ValueError(msg)

    n_segments = segment_dt_s.shape[0]
    phi3 = np.eye(3, dtype=np.float64)
    c3 = np.zeros(3, dtype=np.float64)
    f_list = np.zeros((n_segments, 3, 3), dtype=np.float64)
    g_list = np.zeros((n_segments, 3), dtype=np.float64)

    for index in range(n_segments):
        f_j, g_j, _ = segment_affine_propagator(
            ux=float(segment_ux[index]),
            uy=float(segment_uy[index]),
            delta_omega_rad_s=delta_omega_rad_s,
            dt_s=float(segment_dt_s[index]),
            physics=physics,
        )
        f_list[index] = f_j
        g_list[index] = g_j
        phi3 = f_j @ phi3
        c3 = f_j @ c3 + g_j

    return phi3, c3, f_list, g_list

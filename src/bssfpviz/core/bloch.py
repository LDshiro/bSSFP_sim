"""Exact Bloch generators used in Chapter 3."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from bssfpviz.models.config import PhysicsConfig

FloatArray = npt.NDArray[np.float64]


def bloch_matrix(
    ux: float, uy: float, delta_omega_rad_s: float, physics: PhysicsConfig
) -> FloatArray:
    """Return the 3x3 Bloch generator matrix from the Chapter 3 spec."""
    return np.asarray(
        [
            [-1.0 / physics.t2_s, +delta_omega_rad_s, -uy],
            [-delta_omega_rad_s, -1.0 / physics.t2_s, +ux],
            [+uy, -ux, -1.0 / physics.t1_s],
        ],
        dtype=np.float64,
    )


def bloch_offset_vector(physics: PhysicsConfig) -> FloatArray:
    """Return the affine recovery term `b = [0, 0, M0/T1]^T`."""
    return np.asarray([0.0, 0.0, physics.m0 / physics.t1_s], dtype=np.float64)


def augmented_generator(
    ux: float, uy: float, delta_omega_rad_s: float, physics: PhysicsConfig
) -> FloatArray:
    """Return the 4x4 augmented Bloch generator from the Chapter 3 spec."""
    augmented = np.zeros((4, 4), dtype=np.float64)
    augmented[:3, :3] = bloch_matrix(ux, uy, delta_omega_rad_s, physics)
    augmented[:3, 3] = bloch_offset_vector(physics)
    return augmented

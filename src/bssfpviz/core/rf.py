"""Sequence-independent hard-pulse RF rotation helpers."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def rotation_x(alpha_rad: float) -> FloatArray:
    """Return the right-handed rotation matrix around the x-axis."""
    cos_alpha = float(np.cos(alpha_rad))
    sin_alpha = float(np.sin(alpha_rad))
    return np.asarray(
        [
            [1.0, 0.0, 0.0],
            [0.0, cos_alpha, -sin_alpha],
            [0.0, sin_alpha, cos_alpha],
        ],
        dtype=np.float64,
    )


def rotation_z(phi_rad: float) -> FloatArray:
    """Return the right-handed rotation matrix around the z-axis."""
    cos_phi = float(np.cos(phi_rad))
    sin_phi = float(np.sin(phi_rad))
    return np.asarray(
        [
            [cos_phi, -sin_phi, 0.0],
            [sin_phi, cos_phi, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def hard_pulse_rotation(alpha_rad: float, phi_rad: float) -> FloatArray:
    """Return the real-basis hard-pulse rotation for flip angle and RF phase."""
    return np.asarray(
        rotation_z(phi_rad) @ rotation_x(alpha_rad) @ rotation_z(-phi_rad),
        dtype=np.float64,
    )

"""Sequence-independent affine fixed-point helpers."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def solve_fixed_point(phi3: FloatArray, c3: FloatArray) -> FloatArray:
    """Solve `(I - Phi) @ M = c` for the fixed point of one affine map."""
    phi3 = np.asarray(phi3, dtype=np.float64)
    c3 = np.asarray(c3, dtype=np.float64)
    return np.asarray(np.linalg.solve(np.eye(3, dtype=np.float64) - phi3, c3), dtype=np.float64)


def reconstruct_orbit(
    initial_state: FloatArray,
    f_list: FloatArray,
    g_list: FloatArray,
    boundary_time_s: FloatArray,
) -> FloatArray:
    """Replay one affine recurrence and return the boundary orbit."""
    initial_state = np.asarray(initial_state, dtype=np.float64)
    f_list = np.asarray(f_list, dtype=np.float64)
    g_list = np.asarray(g_list, dtype=np.float64)
    boundary_time_s = np.asarray(boundary_time_s, dtype=np.float64)
    if boundary_time_s.shape != (f_list.shape[0] + 1,):
        msg = "boundary_time_s must align with the segment count."
        raise ValueError(msg)

    orbit_xyz = np.zeros((boundary_time_s.shape[0], 3), dtype=np.float64)
    orbit_xyz[0] = initial_state
    for index in range(f_list.shape[0]):
        orbit_xyz[index + 1] = f_list[index] @ orbit_xyz[index] + g_list[index]
    return orbit_xyz

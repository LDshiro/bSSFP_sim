"""Unit tests for Chapter 3 Bloch generators."""

from __future__ import annotations

import numpy as np

from bssfpviz.core.bloch import augmented_generator, bloch_matrix
from bssfpviz.models.config import PhysicsConfig


def test_bloch_matrix_shapes() -> None:
    physics = PhysicsConfig(t1_s=1.5, t2_s=0.8, m0=1.0)

    matrix = bloch_matrix(ux=1.0, uy=2.0, delta_omega_rad_s=3.0, physics=physics)
    augmented = augmented_generator(ux=1.0, uy=2.0, delta_omega_rad_s=3.0, physics=physics)

    assert matrix.shape == (3, 3)
    assert augmented.shape == (4, 4)


def test_bloch_matrix_matches_relaxation_diagonal_when_controls_are_zero() -> None:
    physics = PhysicsConfig(t1_s=2.0, t2_s=0.5, m0=1.0)

    matrix = bloch_matrix(ux=0.0, uy=0.0, delta_omega_rad_s=0.0, physics=physics)

    np.testing.assert_allclose(np.diag(matrix), np.array([-2.0, -2.0, -0.5], dtype=np.float64))

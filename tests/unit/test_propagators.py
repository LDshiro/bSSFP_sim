"""Unit tests for Chapter 3 segment propagators."""

from __future__ import annotations

import numpy as np

from bssfpviz.core.propagators import segment_affine_propagator
from bssfpviz.models.config import PhysicsConfig


def test_segment_affine_propagator_returns_finite_values() -> None:
    physics = PhysicsConfig(t1_s=0.5, t2_s=0.25, m0=1.0)

    f3, g3, f4 = segment_affine_propagator(1.0, -0.5, 25.0, 1.0e-4, physics)

    assert np.isfinite(f3).all()
    assert np.isfinite(g3).all()
    assert np.isfinite(f4).all()


def test_free_segment_relaxes_mz_toward_m0() -> None:
    physics = PhysicsConfig(t1_s=0.5, t2_s=0.25, m0=1.0)
    f3, g3, _ = segment_affine_propagator(0.0, 0.0, 0.0, 1.0e-2, physics)
    magnetization = np.array([0.0, 0.0, 0.0], dtype=np.float64)
    propagated = f3 @ magnetization + g3

    assert propagated[2] > magnetization[2]
    assert propagated[2] < physics.m0


def test_zero_duration_segment_is_identity() -> None:
    physics = PhysicsConfig()
    f3, g3, _ = segment_affine_propagator(0.0, 0.0, 0.0, 0.0, physics)

    np.testing.assert_allclose(f3, np.eye(3))
    np.testing.assert_allclose(g3, np.zeros(3))

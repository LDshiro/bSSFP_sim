"""Numerical core for sequence-independent Bloch and affine computations."""

from bssfpviz.core.affine import reconstruct_orbit, solve_fixed_point
from bssfpviz.core.bloch import augmented_generator, bloch_matrix, bloch_offset_vector
from bssfpviz.core.propagators import compose_affine_sequence, segment_affine_propagator
from bssfpviz.core.reference import (
    build_affine_reference_grid_spec,
    integrate_reference_trajectory,
    integrate_reference_trajectory_with_affine_grid,
    integrate_reference_trajectory_with_grid,
)

__all__ = [
    "augmented_generator",
    "bloch_matrix",
    "bloch_offset_vector",
    "build_affine_reference_grid_spec",
    "compose_affine_sequence",
    "integrate_reference_trajectory",
    "integrate_reference_trajectory_with_affine_grid",
    "integrate_reference_trajectory_with_grid",
    "reconstruct_orbit",
    "segment_affine_propagator",
    "solve_fixed_point",
]

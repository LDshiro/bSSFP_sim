"""Numerical core for Chapter 3 Bloch, propagator, and steady-state computations."""

from bssfpviz.core.bloch import augmented_generator, bloch_matrix, bloch_offset_vector
from bssfpviz.core.propagators import compose_affine_sequence, segment_affine_propagator
from bssfpviz.core.reference import (
    integrate_reference_trajectory,
    integrate_reference_trajectory_with_grid,
)
from bssfpviz.core.segments import (
    SegmentSequence,
    build_superperiod_segments,
    make_base_rf_waveform,
    materialize_actual_waveforms,
)
from bssfpviz.core.steady_state import (
    compute_readout_profile,
    reconstruct_orbit,
    solve_fixed_point,
)

__all__ = [
    "SegmentSequence",
    "augmented_generator",
    "bloch_matrix",
    "bloch_offset_vector",
    "build_superperiod_segments",
    "compose_affine_sequence",
    "compute_readout_profile",
    "integrate_reference_trajectory",
    "integrate_reference_trajectory_with_grid",
    "make_base_rf_waveform",
    "materialize_actual_waveforms",
    "reconstruct_orbit",
    "segment_affine_propagator",
    "solve_fixed_point",
]

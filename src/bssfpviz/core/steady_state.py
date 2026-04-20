"""Legacy compatibility exports for affine fixed-point and bSSFP readout helpers."""

from bssfpviz.core.affine import reconstruct_orbit, solve_fixed_point
from bssfpviz.sequences.bssfp.sequence import compute_readout_profile

__all__ = [
    "compute_readout_profile",
    "reconstruct_orbit",
    "solve_fixed_point",
]

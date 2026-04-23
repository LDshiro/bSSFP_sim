"""Helpers for manual VFA-FSE trains."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from bssfpviz.models.comparison import VFAFSEFamilyConfig
from bssfpviz.sequences.fse_common import (
    build_echo_time_s as _build_echo_time_s,
)
from bssfpviz.sequences.fse_common import (
    build_event_time_s as _build_event_time_s,
)
from bssfpviz.sequences.fse_common import (
    build_fid_time_s as _build_fid_time_s,
)
from bssfpviz.sequences.fse_common import (
    build_flip_train_deg as _build_flip_train_deg,
)
from bssfpviz.sequences.fse_common import (
    build_iso_positions as _build_iso_positions,
)
from bssfpviz.sequences.fse_common import (
    build_phase_train_deg as _build_phase_train_deg,
)
from bssfpviz.sequences.fse_common import (
    compute_te_center_k_ms as _compute_te_center_k_ms,
)

FloatArray = npt.NDArray[np.float64]


def build_iso_positions(n_iso: int) -> FloatArray:
    """Return the effective-1D isochromat positions on [-0.5, 0.5)."""
    return _build_iso_positions(n_iso)


def build_echo_time_s(config: VFAFSEFamilyConfig) -> FloatArray:
    """Return echo-center sampling times for one echo train."""
    return _build_echo_time_s(etl=config.etl, esp_ms=config.esp_ms)


def build_fid_time_s(config: VFAFSEFamilyConfig) -> FloatArray:
    """Return FID sampling times immediately after refocusing pulses."""
    return _build_fid_time_s(etl=config.etl, esp_ms=config.esp_ms)


def build_event_time_s(config: VFAFSEFamilyConfig) -> FloatArray:
    """Return [excitation, fid_1, echo_1, ..., fid_ETL, echo_ETL] event times."""
    return _build_event_time_s(etl=config.etl, esp_ms=config.esp_ms)


def build_flip_train_deg(config: VFAFSEFamilyConfig) -> FloatArray:
    """Return [alpha_exc, alpha_ref_1, ..., alpha_ref_ETL]."""
    return _build_flip_train_deg(
        alpha_exc_deg=config.alpha_exc_deg,
        alpha_ref_train_deg=config.alpha_ref_train_deg,
    )


def build_phase_train_deg(config: VFAFSEFamilyConfig) -> FloatArray:
    """Return [phi_exc, phi_ref_1, ..., phi_ref_ETL]."""
    if config.phi_ref_train_deg is None:
        msg = "phi_ref_train_deg must be resolved before building the VFA phase train."
        raise ValueError(msg)
    return _build_phase_train_deg(
        phi_exc_deg=config.phi_exc_deg,
        phi_ref_train_deg=config.phi_ref_train_deg,
    )


def compute_te_center_k_ms(config: VFAFSEFamilyConfig) -> float:
    """Return the center-k echo time using the middle echo of the train."""
    return _compute_te_center_k_ms(etl=config.etl, esp_ms=config.esp_ms)

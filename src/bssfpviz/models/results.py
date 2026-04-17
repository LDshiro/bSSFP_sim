"""Result models for Chapter 3 solver outputs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from bssfpviz.models.config import SimulationConfig, SimulationMetadata

ComplexArray = npt.NDArray[np.complex128]
FloatArray = npt.NDArray[np.float64]


def _as_float_array(value: object, *, ndim: int, name: str) -> FloatArray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != ndim:
        msg = f"{name} must be a {ndim}D float array."
        raise ValueError(msg)
    return np.array(array, dtype=np.float64, copy=True)


def _as_complex_array(value: object, *, ndim: int, name: str) -> ComplexArray:
    array = np.asarray(value, dtype=np.complex128)
    if array.ndim != ndim:
        msg = f"{name} must be a {ndim}D complex array."
        raise ValueError(msg)
    return np.array(array, dtype=np.complex128, copy=True)


@dataclass(slots=True)
class SimulationDataset:
    """Simulation inputs and outputs saved in Chapter 3.

    Shapes:
    - `rf_xy`: `(n_rf_samples, 2)`
    - `reference_time_s`: `(n_reference_time,)`
    - `steady_state_time_s`: `(n_steady_time,)`
    - `reference_m_xyz`: `(n_acq, n_spins, n_reference_time, 3)`
    - `steady_state_orbit_xyz`: `(n_acq, n_spins, n_steady_time, 3)`
    - `steady_state_fixed_point_xyz`: `(n_acq, n_spins, 3)`
    - `individual_profile_complex`: `(n_acq, n_spins)`
    - `sos_profile_magnitude`: `(n_spins,)`
    """

    metadata: SimulationMetadata
    config: SimulationConfig
    rf_xy: FloatArray
    reference_time_s: FloatArray
    steady_state_time_s: FloatArray
    reference_m_xyz: FloatArray
    steady_state_orbit_xyz: FloatArray
    steady_state_fixed_point_xyz: FloatArray
    individual_profile_complex: ComplexArray
    sos_profile_magnitude: FloatArray

    def __post_init__(self) -> None:
        self.rf_xy = _as_float_array(self.rf_xy, ndim=2, name="rf_xy")
        self.reference_time_s = _as_float_array(
            self.reference_time_s, ndim=1, name="reference_time_s"
        )
        self.steady_state_time_s = _as_float_array(
            self.steady_state_time_s, ndim=1, name="steady_state_time_s"
        )
        self.reference_m_xyz = _as_float_array(self.reference_m_xyz, ndim=4, name="reference_m_xyz")
        self.steady_state_orbit_xyz = _as_float_array(
            self.steady_state_orbit_xyz, ndim=4, name="steady_state_orbit_xyz"
        )
        self.steady_state_fixed_point_xyz = _as_float_array(
            self.steady_state_fixed_point_xyz, ndim=3, name="steady_state_fixed_point_xyz"
        )
        self.individual_profile_complex = _as_complex_array(
            self.individual_profile_complex, ndim=2, name="individual_profile_complex"
        )
        self.sos_profile_magnitude = _as_float_array(
            self.sos_profile_magnitude, ndim=1, name="sos_profile_magnitude"
        )
        self._validate_shapes()
        self._validate_time_axes()
        self._validate_sos_profile()

    def _validate_shapes(self) -> None:
        n_spins = self.config.n_spins
        n_acquisitions = self.config.n_acquisitions
        n_reference_time = self.config.sampling.n_reference_steps
        n_steady_time = self.config.sampling.n_steady_state_steps
        n_rf_samples = self.config.sequence.n_rf_samples

        if self.rf_xy.shape != (n_rf_samples, 2):
            msg = f"rf_xy must have shape ({n_rf_samples}, 2)."
            raise ValueError(msg)
        if self.reference_time_s.shape != (n_reference_time,):
            msg = f"reference_time_s must have shape ({n_reference_time},)."
            raise ValueError(msg)
        if self.steady_state_time_s.shape != (n_steady_time,):
            msg = f"steady_state_time_s must have shape ({n_steady_time},)."
            raise ValueError(msg)
        if self.reference_m_xyz.shape != (n_acquisitions, n_spins, n_reference_time, 3):
            msg = (
                "reference_m_xyz must have shape "
                f"({n_acquisitions}, {n_spins}, {n_reference_time}, 3)."
            )
            raise ValueError(msg)
        if self.steady_state_orbit_xyz.shape != (n_acquisitions, n_spins, n_steady_time, 3):
            msg = (
                "steady_state_orbit_xyz must have shape "
                f"({n_acquisitions}, {n_spins}, {n_steady_time}, 3)."
            )
            raise ValueError(msg)
        if self.steady_state_fixed_point_xyz.shape != (n_acquisitions, n_spins, 3):
            msg = f"steady_state_fixed_point_xyz must have shape ({n_acquisitions}, {n_spins}, 3)."
            raise ValueError(msg)
        if self.individual_profile_complex.shape != (n_acquisitions, n_spins):
            msg = f"individual_profile_complex must have shape ({n_acquisitions}, {n_spins})."
            raise ValueError(msg)
        if self.sos_profile_magnitude.shape != (n_spins,):
            msg = f"sos_profile_magnitude must have shape ({n_spins},)."
            raise ValueError(msg)

    def _validate_time_axes(self) -> None:
        if not np.all(np.diff(self.reference_time_s) > 0.0):
            msg = "reference_time_s must be strictly increasing."
            raise ValueError(msg)
        if not np.all(np.diff(self.steady_state_time_s) > 0.0):
            msg = "steady_state_time_s must be strictly increasing."
            raise ValueError(msg)
        if not np.isclose(self.reference_time_s[0], 0.0):
            msg = "reference_time_s must start at 0."
            raise ValueError(msg)
        if not np.isclose(self.steady_state_time_s[0], 0.0):
            msg = "steady_state_time_s must start at 0."
            raise ValueError(msg)

    def _validate_sos_profile(self) -> None:
        expected = np.sqrt(np.sum(np.abs(self.individual_profile_complex) ** 2, axis=0))
        if not np.allclose(self.sos_profile_magnitude, expected, atol=1e-10, rtol=1e-10):
            msg = "sos_profile_magnitude must match individual_profile_complex."
            raise ValueError(msg)

"""Normalized view-model for Chapter 6 synchronized observation widgets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import numpy as np
import numpy.typing as npt

from bssfpviz.gui.adapters import LoadedDatasetView
from bssfpviz.models.results import SimulationDataset

ComplexArray = npt.NDArray[np.complex128]
FloatArray = npt.NDArray[np.float64]


@dataclass(slots=True)
class DatasetViewModel:
    """Normalized dataset access for synchronized 3D and 2D playback."""

    dataset: SimulationDataset
    delta_f_hz: FloatArray
    n_acq: int
    n_spins: int
    n_reference_frames: int
    n_steady_frames: int
    _reference_time_s: FloatArray = field(repr=False)
    _steady_time_s: FloatArray = field(repr=False)
    _reference_m_xyz: FloatArray = field(repr=False)
    _steady_state_orbit_xyz: FloatArray = field(repr=False)
    _steady_state_fixed_point_xyz: FloatArray | None = field(default=None, repr=False)
    _individual_profile_complex: ComplexArray | None = field(default=None, repr=False)
    _sos_profile_magnitude: FloatArray | None = field(default=None, repr=False)

    @classmethod
    def from_dataset(cls, dataset: SimulationDataset) -> DatasetViewModel:
        """Build a view-model from the canonical Chapter 3 dataset model."""
        delta_f_hz = _extract_delta_f_hz(dataset)
        return cls(
            dataset=dataset,
            delta_f_hz=delta_f_hz,
            n_acq=int(dataset.reference_m_xyz.shape[0]),
            n_spins=int(dataset.reference_m_xyz.shape[1]),
            n_reference_frames=int(dataset.reference_m_xyz.shape[2]),
            n_steady_frames=int(dataset.steady_state_orbit_xyz.shape[2]),
            _reference_time_s=np.asarray(dataset.reference_time_s, dtype=np.float64),
            _steady_time_s=np.asarray(dataset.steady_state_time_s, dtype=np.float64),
            _reference_m_xyz=np.asarray(dataset.reference_m_xyz, dtype=np.float64),
            _steady_state_orbit_xyz=np.asarray(dataset.steady_state_orbit_xyz, dtype=np.float64),
            _steady_state_fixed_point_xyz=np.asarray(
                dataset.steady_state_fixed_point_xyz, dtype=np.float64
            ),
            _individual_profile_complex=np.asarray(
                dataset.individual_profile_complex, dtype=np.complex128
            ),
            _sos_profile_magnitude=np.asarray(dataset.sos_profile_magnitude, dtype=np.float64),
        )

    @classmethod
    def from_loaded_view(cls, view: LoadedDatasetView) -> DatasetViewModel:
        """Build a view-model from the Chapter 5 GUI adapter dataset view."""
        if (
            view.delta_f_hz is None
            or view.rk_time_s is None
            or view.rk_magnetization is None
            or view.steady_state_time_s is None
            or view.steady_state_orbit is None
        ):
            msg = "LoadedDatasetView is missing trajectory arrays required for playback."
            raise ValueError(msg)

        n_spins = int(view.delta_f_hz.shape[0])
        n_acq = int(view.rk_magnetization.shape[1])
        reference_m_xyz = np.transpose(view.rk_magnetization, (1, 0, 2, 3))
        steady_state_orbit_xyz = np.transpose(view.steady_state_orbit, (1, 0, 2, 3))
        fixed_points = None
        if view.steady_state_fixed_points is not None:
            fixed_points = np.transpose(view.steady_state_fixed_points, (1, 0, 2))

        individual_profile_complex = None
        if view.profiles_complex_real is not None and view.profiles_complex_imag is not None:
            individual_profile_complex = np.asarray(
                (view.profiles_complex_real + 1j * view.profiles_complex_imag).T,
                dtype=np.complex128,
            )

        return cls(
            dataset=cast(SimulationDataset, view),
            delta_f_hz=np.asarray(view.delta_f_hz, dtype=np.float64),
            n_acq=n_acq,
            n_spins=n_spins,
            n_reference_frames=int(view.rk_time_s.shape[0]),
            n_steady_frames=int(view.steady_state_time_s.shape[0]),
            _reference_time_s=np.asarray(view.rk_time_s, dtype=np.float64),
            _steady_time_s=np.asarray(view.steady_state_time_s, dtype=np.float64),
            _reference_m_xyz=np.asarray(reference_m_xyz, dtype=np.float64),
            _steady_state_orbit_xyz=np.asarray(steady_state_orbit_xyz, dtype=np.float64),
            _steady_state_fixed_point_xyz=(
                None if fixed_points is None else np.asarray(fixed_points, dtype=np.float64)
            ),
            _individual_profile_complex=individual_profile_complex,
            _sos_profile_magnitude=(
                None
                if view.profiles_sos is None
                else np.asarray(view.profiles_sos, dtype=np.float64)
            ),
        )

    def __post_init__(self) -> None:
        self.delta_f_hz = np.asarray(self.delta_f_hz, dtype=np.float64)
        self._reference_time_s = np.asarray(self._reference_time_s, dtype=np.float64)
        self._steady_time_s = np.asarray(self._steady_time_s, dtype=np.float64)
        self._reference_m_xyz = np.asarray(self._reference_m_xyz, dtype=np.float64)
        self._steady_state_orbit_xyz = np.asarray(self._steady_state_orbit_xyz, dtype=np.float64)
        if self._steady_state_fixed_point_xyz is not None:
            self._steady_state_fixed_point_xyz = np.asarray(
                self._steady_state_fixed_point_xyz, dtype=np.float64
            )
        if self._individual_profile_complex is not None:
            self._individual_profile_complex = np.asarray(
                self._individual_profile_complex, dtype=np.complex128
            )
        if self._sos_profile_magnitude is not None:
            self._sos_profile_magnitude = np.asarray(self._sos_profile_magnitude, dtype=np.float64)
        self._validate_shapes()

    def get_frame_count(self, mode: str) -> int:
        """Return the frame count for `reference` or `steady` mode."""
        normalized_mode = _normalize_mode(mode)
        return self.n_reference_frames if normalized_mode == "reference" else self.n_steady_frames

    def get_time_array_s(self, mode: str) -> FloatArray:
        """Return the frame time axis for the requested mode."""
        normalized_mode = _normalize_mode(mode)
        return self._reference_time_s if normalized_mode == "reference" else self._steady_time_s

    def get_vectors_xyz(self, mode: str, acquisition_index: int, frame_index: int) -> FloatArray:
        """Return `(n_spins, 3)` vectors for one acquisition/frame."""
        normalized_mode = _normalize_mode(mode)
        acq = self._clamp_acquisition_index(acquisition_index)
        frame = self._clamp_frame_index(normalized_mode, frame_index)
        data = (
            self._reference_m_xyz
            if normalized_mode == "reference"
            else self._steady_state_orbit_xyz
        )
        return data[acq, :, frame, :]

    def get_spin_series_xyz(self, mode: str, acquisition_index: int, spin_index: int) -> FloatArray:
        """Return `(n_frames, 3)` for one acquisition/spin pair."""
        normalized_mode = _normalize_mode(mode)
        acq = self._clamp_acquisition_index(acquisition_index)
        spin = self._clamp_spin_index(spin_index)
        data = (
            self._reference_m_xyz
            if normalized_mode == "reference"
            else self._steady_state_orbit_xyz
        )
        return data[acq, spin, :, :]

    def get_mean_transverse_magnitude_series(
        self,
        mode: str,
        acquisition_index: int,
    ) -> FloatArray:
        """Return `sqrt(mean(Mx)^2 + mean(My)^2)` over spins for each frame."""
        normalized_mode = _normalize_mode(mode)
        acq = self._clamp_acquisition_index(acquisition_index)
        data = (
            self._reference_m_xyz
            if normalized_mode == "reference"
            else self._steady_state_orbit_xyz
        )
        mean_xy = np.mean(data[acq, :, :, :2], axis=0)
        return np.hypot(mean_xy[:, 0], mean_xy[:, 1])

    def get_current_time_s(self, mode: str, frame_index: int) -> float:
        """Return the current time sample for the requested mode/frame."""
        normalized_mode = _normalize_mode(mode)
        frame = self._clamp_frame_index(normalized_mode, frame_index)
        time_array = self.get_time_array_s(normalized_mode)
        return float(time_array[frame])

    def get_profile_complex(self, acquisition_index: int) -> ComplexArray:
        """Return `(n_spins,)` complex individual profile for one acquisition."""
        if self._individual_profile_complex is None:
            return np.zeros(self.n_spins, dtype=np.complex128)
        acq = self._clamp_acquisition_index(acquisition_index)
        return self._individual_profile_complex[acq, :]

    def get_sos_profile(self) -> FloatArray:
        """Return `(n_spins,)` SOS profile magnitude."""
        if self._sos_profile_magnitude is None:
            return np.zeros(self.n_spins, dtype=np.float64)
        return self._sos_profile_magnitude

    def get_steady_orbit_xyz(self, acquisition_index: int) -> FloatArray:
        """Return `(n_spins, n_steady_frames, 3)` steady-state orbit for one acquisition."""
        acq = self._clamp_acquisition_index(acquisition_index)
        return self._steady_state_orbit_xyz[acq, :, :, :]

    def get_selected_delta_f_hz(self, spin_index: int) -> float:
        """Return the off-resonance value for the selected spin."""
        spin = self._clamp_spin_index(spin_index)
        return float(self.delta_f_hz[spin])

    def get_fixed_point_xyz(self, acquisition_index: int, spin_index: int) -> FloatArray | None:
        """Return `(3,)` fixed point for one acquisition/spin pair if available."""
        if self._steady_state_fixed_point_xyz is None:
            return None
        acq = self._clamp_acquisition_index(acquisition_index)
        spin = self._clamp_spin_index(spin_index)
        return self._steady_state_fixed_point_xyz[acq, spin, :]

    def _validate_shapes(self) -> None:
        if self.delta_f_hz.shape != (self.n_spins,):
            msg = f"delta_f_hz must have shape ({self.n_spins},)."
            raise ValueError(msg)
        if self._reference_time_s.shape != (self.n_reference_frames,):
            msg = f"reference_time_s must have shape ({self.n_reference_frames},)."
            raise ValueError(msg)
        if self._steady_time_s.shape != (self.n_steady_frames,):
            msg = f"steady_state_time_s must have shape ({self.n_steady_frames},)."
            raise ValueError(msg)
        if self._reference_m_xyz.shape != (self.n_acq, self.n_spins, self.n_reference_frames, 3):
            msg = "reference_m_xyz shape does not match declared counts."
            raise ValueError(msg)
        if self._steady_state_orbit_xyz.shape != (
            self.n_acq,
            self.n_spins,
            self.n_steady_frames,
            3,
        ):
            msg = "steady_state_orbit_xyz shape does not match declared counts."
            raise ValueError(msg)
        if (
            self._steady_state_fixed_point_xyz is not None
            and self._steady_state_fixed_point_xyz.shape != (self.n_acq, self.n_spins, 3)
        ):
            msg = "steady_state_fixed_point_xyz shape does not match declared counts."
            raise ValueError(msg)
        if (
            self._individual_profile_complex is not None
            and self._individual_profile_complex.shape != (self.n_acq, self.n_spins)
        ):
            msg = "individual_profile_complex shape does not match declared counts."
            raise ValueError(msg)
        if self._sos_profile_magnitude is not None and self._sos_profile_magnitude.shape != (
            self.n_spins,
        ):
            msg = "sos_profile_magnitude shape does not match declared counts."
            raise ValueError(msg)

    def _clamp_acquisition_index(self, index: int) -> int:
        return max(0, min(index, self.n_acq - 1))

    def _clamp_spin_index(self, index: int) -> int:
        return max(0, min(index, self.n_spins - 1))

    def _clamp_frame_index(self, mode: str, index: int) -> int:
        frame_count = self.get_frame_count(mode)
        return max(0, min(index, frame_count - 1))


def _normalize_mode(mode: str) -> str:
    if mode == "steady-state":
        return "steady"
    if mode not in {"reference", "steady"}:
        msg = f"Unsupported playback mode: {mode!r}"
        raise ValueError(msg)
    return mode


def _extract_delta_f_hz(dataset: SimulationDataset) -> FloatArray:
    if hasattr(dataset.config, "sampling") and hasattr(dataset.config.sampling, "delta_f_hz"):
        return np.asarray(dataset.config.sampling.delta_f_hz, dtype=np.float64)
    msg = "Could not extract delta_f_hz from dataset."
    raise ValueError(msg)

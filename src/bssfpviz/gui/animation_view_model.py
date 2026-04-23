"""Generic animation view-models for bundle-driven 3D observation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from bssfpviz.models.comparison import SequenceFamily, SimulationResult

FloatArray = npt.NDArray[np.float64]


@dataclass(slots=True)
class AnimationViewModel:
    """ScenePanel-compatible view-model built from a generic SimulationResult."""

    run_label: str
    sequence_family: SequenceFamily
    selector_label: str
    selector_values: FloatArray
    n_acq: int
    n_spins: int
    n_reference_frames: int
    n_steady_frames: int
    _reference_time_s: FloatArray
    _steady_time_s: FloatArray
    _reference_m_xyz: FloatArray
    _steady_state_orbit_xyz: FloatArray

    @classmethod
    def from_simulation_result(cls, result: SimulationResult) -> AnimationViewModel:
        """Build an animation view-model from one generic result branch."""
        if result.sequence_family == SequenceFamily.BSSFP:
            return cls._from_bssfp_result(result)
        if result.sequence_family in {SequenceFamily.FASTSE, SequenceFamily.VFA_FSE}:
            return cls._from_fse_result(result)
        msg = f"Unsupported family for animation: {result.sequence_family.value}"
        raise ValueError(msg)

    @classmethod
    def _from_fse_result(cls, result: SimulationResult) -> AnimationViewModel:
        event_m = np.asarray(result.trajectories["event_m"], dtype=np.float64)
        if event_m.ndim != 3 or event_m.shape[2] != 3:
            msg = "FSE event_m must have shape (n_frames, n_iso, 3)."
            raise ValueError(msg)
        reference_m = np.transpose(event_m, (1, 0, 2))[np.newaxis, :, :, :]
        event_time_s = np.asarray(result.axes["event_time_s"], dtype=np.float64)
        selector_values = np.asarray(result.axes["iso_position"], dtype=np.float64)
        return cls(
            run_label=result.run_label,
            sequence_family=result.sequence_family,
            selector_label="iso_position",
            selector_values=selector_values,
            n_acq=1,
            n_spins=int(reference_m.shape[1]),
            n_reference_frames=int(reference_m.shape[2]),
            n_steady_frames=int(reference_m.shape[2]),
            _reference_time_s=event_time_s,
            _steady_time_s=event_time_s,
            _reference_m_xyz=reference_m,
            _steady_state_orbit_xyz=reference_m,
        )

    @classmethod
    def _from_bssfp_result(cls, result: SimulationResult) -> AnimationViewModel:
        reference_m = np.asarray(result.trajectories["reference_m"], dtype=np.float64)
        steady_m = np.asarray(result.trajectories["steady_state_orbit_m"], dtype=np.float64)
        if reference_m.ndim != 4 or steady_m.ndim != 4:
            msg = "BSSFP reference and steady trajectories must be 4D."
            raise ValueError(msg)
        reference_m = np.transpose(reference_m, (1, 0, 2, 3))
        steady_m = np.transpose(steady_m, (1, 0, 2, 3))
        return cls(
            run_label=result.run_label,
            sequence_family=result.sequence_family,
            selector_label="delta_f_hz",
            selector_values=np.asarray(result.axes["delta_f_hz"], dtype=np.float64),
            n_acq=int(reference_m.shape[0]),
            n_spins=int(reference_m.shape[1]),
            n_reference_frames=int(reference_m.shape[2]),
            n_steady_frames=int(steady_m.shape[2]),
            _reference_time_s=np.asarray(result.axes["reference_time_s"], dtype=np.float64),
            _steady_time_s=np.asarray(result.axes["steady_state_time_s"], dtype=np.float64),
            _reference_m_xyz=reference_m,
            _steady_state_orbit_xyz=steady_m,
        )

    def get_frame_count(self, mode: str) -> int:
        """Return frame count for `reference` or `steady` mode."""
        if _normalize_mode(mode) == "steady":
            return self.n_steady_frames
        return self.n_reference_frames

    def get_time_array_s(self, mode: str) -> FloatArray:
        """Return the time axis for one playback mode."""
        return self._steady_time_s if _normalize_mode(mode) == "steady" else self._reference_time_s

    def get_current_time_s(self, mode: str, frame_index: int) -> float:
        """Return one clamped frame time."""
        frame = max(0, min(int(frame_index), self.get_frame_count(mode) - 1))
        return float(self.get_time_array_s(mode)[frame])

    def get_vectors_xyz(self, mode: str, acquisition_index: int, frame_index: int) -> FloatArray:
        """Return `(n_spins, 3)` vectors for the requested frame."""
        data = self._data_for_mode(mode)
        acq = max(0, min(int(acquisition_index), self.n_acq - 1))
        frame = max(0, min(int(frame_index), data.shape[2] - 1))
        return np.asarray(data[acq, :, frame, :], dtype=np.float64)

    def get_spin_series_xyz(self, mode: str, acquisition_index: int, spin_index: int) -> FloatArray:
        """Return `(n_frames, 3)` for one selector entity."""
        data = self._data_for_mode(mode)
        acq = max(0, min(int(acquisition_index), self.n_acq - 1))
        spin = max(0, min(int(spin_index), self.n_spins - 1))
        return np.asarray(data[acq, spin, :, :], dtype=np.float64)

    def get_steady_orbit_xyz(self, acquisition_index: int) -> FloatArray:
        """Return `(n_spins, n_frames, 3)` static orbit lines."""
        acq = max(0, min(int(acquisition_index), self.n_acq - 1))
        return np.asarray(self._steady_state_orbit_xyz[acq, :, :, :], dtype=np.float64)

    def get_selected_delta_f_hz(self, spin_index: int) -> float:
        """Return a numeric selector value for ScenePanel fallback text."""
        spin = max(0, min(int(spin_index), self.n_spins - 1))
        return float(self.selector_values[spin])

    def _data_for_mode(self, mode: str) -> FloatArray:
        return (
            self._steady_state_orbit_xyz
            if _normalize_mode(mode) == "steady"
            else self._reference_m_xyz
        )


def _normalize_mode(mode: str) -> str:
    if mode == "steady-state":
        return "steady"
    if mode not in {"reference", "steady"}:
        msg = f"Unsupported animation mode: {mode!r}"
        raise ValueError(msg)
    return mode

"""Comparison-aware playback controller for Chapter 7."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from PySide6.QtCore import QObject, Qt, QTimer, Signal

from bssfpviz.gui.dataset_view_model import DatasetViewModel
from bssfpviz.gui.playback_controller import PlaybackState
from bssfpviz.gui.session_state import SessionState


@dataclass(slots=True)
class ResolvedSelection:
    """One resolved slot/acquisition/spin/frame selection."""

    slot: str
    acquisition_index: int
    spin_index: int
    frame_index: int
    delta_f_hz: float


@dataclass(slots=True)
class ComparisonModel:
    """Loaded dataset view-models for the comparison GUI."""

    primary_vm: DatasetViewModel | None = None
    compare_vm: DatasetViewModel | None = None


class ComparisonController(QObject):
    """Own the active/compare mapping rules and playback state."""

    state_changed = Signal()
    datasets_changed = Signal()
    selection_changed = Signal()
    bookmarks_changed = Signal()
    frame_changed = Signal(int)
    mode_changed = Signal(str)
    acquisition_changed = Signal(int)
    spin_changed = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = SessionState()
        self._model = ComparisonModel()
        self._is_playing = False
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self.step_forward)
        self._update_timer_interval()

    def set_primary_dataset(self, vm: DatasetViewModel | None, path: str | None = None) -> None:
        """Set or clear the primary dataset."""
        previous = self.resolve_active_selection()
        self._model.primary_vm = vm
        self._session.primary_path = path
        self._clamp_state()
        self.datasets_changed.emit()
        self._emit_resolved_change(previous)
        self.selection_changed.emit()
        self.state_changed.emit()

    def set_compare_dataset(self, vm: DatasetViewModel | None, path: str | None = None) -> None:
        """Set or clear the compare dataset."""
        previous = self.resolve_active_selection()
        self._model.compare_vm = vm
        self._session.compare_path = path
        if vm is None and self._session.active_slot == "compare":
            self._session = replace(self._session, active_slot="primary")
        self._clamp_state()
        self.datasets_changed.emit()
        self._emit_resolved_change(previous)
        self.selection_changed.emit()
        self.state_changed.emit()

    def set_active_slot(self, slot: str) -> None:
        """Select which slot drives canonical selection and playback."""
        if slot not in {"primary", "compare"}:
            msg = "slot must be 'primary' or 'compare'."
            raise ValueError(msg)
        previous = self.resolve_active_selection()
        self._session = replace(self._session, active_slot=slot)
        self._clamp_state()
        self._emit_resolved_change(previous)
        self.selection_changed.emit()
        self.state_changed.emit()

    def set_compare_enabled(self, enabled: bool) -> None:
        """Enable or disable compare overlays."""
        self._session = replace(self._session, compare_enabled=bool(enabled))
        self.selection_changed.emit()
        self.state_changed.emit()

    def set_compare_visible_in_scene(self, visible: bool) -> None:
        """Control whether compare data is drawn in the scene."""
        self._session = replace(self._session, compare_visible_in_scene=bool(visible))
        self.selection_changed.emit()
        self.state_changed.emit()

    def set_thick_all_spins_in_scene(self, enabled: bool) -> None:
        """Control whether all active spins use emphasized scene line widths."""
        self._session = replace(self._session, thick_all_spins_in_scene=bool(enabled))
        self.selection_changed.emit()
        self.state_changed.emit()

    def set_mode(self, mode: str) -> None:
        """Set the global playback mode."""
        normalized = _normalize_mode(mode)
        previous = self.resolve_active_selection()
        self._session = replace(self._session, mode=normalized)
        self._clamp_state()
        self.mode_changed.emit(normalized)
        self._emit_resolved_change(previous)
        self.selection_changed.emit()
        self.state_changed.emit()

    def set_acquisition_index(self, index: int) -> None:
        """Set the active acquisition index."""
        previous = self.resolve_active_selection()
        self._session = replace(self._session, acquisition_index=max(0, int(index)))
        self._clamp_state()
        self._emit_resolved_change(previous)
        self.selection_changed.emit()
        self.state_changed.emit()

    def set_frame_index(self, index: int) -> None:
        """Set the active frame index."""
        previous_index = self._session.frame_index
        self._session = replace(self._session, frame_index=max(0, int(index)))
        self._clamp_state()
        if self._session.frame_index != previous_index:
            self.frame_changed.emit(self._session.frame_index)

    def set_spin_index(self, index: int) -> None:
        """Compatibility helper that maps a spin index to canonical delta-f."""
        active_vm = self.get_active_vm()
        if active_vm is None:
            return
        clamped = max(0, min(int(index), active_vm.n_spins - 1))
        self.set_selected_delta_f_hz(active_vm.get_selected_delta_f_hz(clamped))

    def set_selected_delta_f_hz(self, delta_f_hz: float) -> None:
        """Set the canonical selected off-resonance value."""
        previous = self.resolve_active_selection()
        self._session = replace(self._session, selected_delta_f_hz=float(delta_f_hz))
        self._clamp_state()
        self._emit_resolved_change(previous)
        self.selection_changed.emit()
        self.state_changed.emit()

    def add_bookmark(self, delta_f_hz: float | None = None) -> None:
        """Add one bookmark using the supplied or current delta-f value."""
        value = self.get_current_delta_f_hz() if delta_f_hz is None else float(delta_f_hz)
        if value is None:
            return
        bookmarks = list(self._session.bookmarks_hz)
        bookmarks.append(value)
        session = replace(self._session, bookmarks_hz=bookmarks)
        self._session = replace(session, bookmarks_hz=session.normalized_bookmarks())
        self.bookmarks_changed.emit()
        self.state_changed.emit()

    def remove_bookmark(self, delta_f_hz: float) -> None:
        """Remove the nearest matching bookmark within 1e-9 tolerance."""
        bookmarks = [
            value for value in self._session.bookmarks_hz if abs(value - float(delta_f_hz)) > 1.0e-9
        ]
        self._session = replace(self._session, bookmarks_hz=bookmarks)
        self.bookmarks_changed.emit()
        self.state_changed.emit()

    def jump_to_bookmark(self, delta_f_hz: float) -> None:
        """Select one bookmark as the current canonical delta-f."""
        self.set_selected_delta_f_hz(float(delta_f_hz))

    def get_active_vm(self) -> DatasetViewModel | None:
        """Return the currently active dataset view-model."""
        return self._vm_for_slot(self._session.active_slot)

    def get_other_vm(self) -> DatasetViewModel | None:
        """Return the non-active dataset view-model."""
        return self._vm_for_slot(_other_slot(self._session.active_slot))

    def resolve_active_selection(self) -> ResolvedSelection | None:
        """Resolve the active slot selection using nearest-delta matching."""
        vm = self.get_active_vm()
        if vm is None:
            return None

        acquisition_index = min(self._session.acquisition_index, vm.n_acq - 1)
        if self._session.selected_delta_f_hz is None:
            spin_index = 0
        else:
            spin_index = _nearest_spin_index(vm.delta_f_hz, self._session.selected_delta_f_hz)
        frame_index = _clamp_frame_index(
            vm.get_frame_count(self._session.mode), self._session.frame_index
        )
        delta_f_hz = float(vm.delta_f_hz[spin_index])
        return ResolvedSelection(
            slot=self._session.active_slot,
            acquisition_index=acquisition_index,
            spin_index=spin_index,
            frame_index=frame_index,
            delta_f_hz=delta_f_hz,
        )

    def resolve_other_selection(self) -> ResolvedSelection | None:
        """Resolve the non-active selection using Chapter 7 mapping rules."""
        if not self._session.compare_enabled:
            return None
        active = self.resolve_active_selection()
        other_vm = self.get_other_vm()
        if active is None or other_vm is None:
            return None

        acquisition_index = min(active.acquisition_index, other_vm.n_acq - 1)
        spin_index = _nearest_spin_index(other_vm.delta_f_hz, active.delta_f_hz)

        active_vm = self.get_active_vm()
        if active_vm is None:
            return None
        na = active_vm.get_frame_count(self._session.mode)
        nb = other_vm.get_frame_count(self._session.mode)
        mapped_frame = _map_frame_index(active.frame_index, na, nb)

        return ResolvedSelection(
            slot=_other_slot(self._session.active_slot),
            acquisition_index=acquisition_index,
            spin_index=spin_index,
            frame_index=mapped_frame,
            delta_f_hz=float(other_vm.delta_f_hz[spin_index]),
        )

    def get_current_delta_f_hz(self) -> float | None:
        """Return the active selection delta-f value if resolvable."""
        active = self.resolve_active_selection()
        return None if active is None else active.delta_f_hz

    def state(self) -> PlaybackState:
        """Return a Chapter 6-compatible playback state snapshot."""
        return PlaybackState(
            mode=self._session.mode,
            acquisition_index=self._session.acquisition_index,
            spin_index=self._resolved_spin_index_or_zero(),
            frame_index=self._session.frame_index,
            is_playing=self._is_playing,
            loop=self._session.loop,
            fps=self._session.fps,
        )

    def session_state(self) -> SessionState:
        """Return a copy of the current session state."""
        return replace(self._session, bookmarks_hz=list(self._session.bookmarks_hz))

    def set_session_state(self, session: SessionState) -> None:
        """Replace the current session state."""
        self.stop()
        previous = self.resolve_active_selection()
        self._session = replace(session, bookmarks_hz=session.normalized_bookmarks())
        self._clamp_state()
        self.bookmarks_changed.emit()
        self.mode_changed.emit(self._session.mode)
        self._emit_resolved_change(previous)
        self.selection_changed.emit()
        self.state_changed.emit()

    def view_model(self) -> DatasetViewModel | None:
        """Compatibility alias used by the playback bar."""
        return self.get_active_vm()

    def set_fps(self, fps: float) -> None:
        """Update playback speed."""
        self._session = replace(self._session, fps=max(0.1, float(fps)))
        self._update_timer_interval()
        self.state_changed.emit()

    def set_loop(self, enabled: bool) -> None:
        """Enable or disable playback looping."""
        self._session = replace(self._session, loop=bool(enabled))
        self.state_changed.emit()

    def toggle_play(self) -> None:
        """Toggle timer-driven playback."""
        if self.get_active_vm() is None:
            return
        if self._is_playing:
            self.stop()
            return
        self._is_playing = True
        self._update_timer_interval()
        self._timer.start()
        self.state_changed.emit()

    def stop(self) -> None:
        """Stop timer-driven playback."""
        if self._timer.isActive():
            self._timer.stop()
        if self._is_playing:
            self._is_playing = False
            self.state_changed.emit()

    def step_forward(self) -> None:
        """Advance one frame using the active dataset frame count."""
        active_vm = self.get_active_vm()
        if active_vm is None:
            return
        frame_count = active_vm.get_frame_count(self._session.mode)
        if self._session.frame_index + 1 < frame_count:
            self.set_frame_index(self._session.frame_index + 1)
            return
        if self._session.loop:
            self.set_frame_index(0)
            return
        self.stop()

    def step_backward(self) -> None:
        """Move one frame backward using the active dataset frame count."""
        if self.get_active_vm() is None:
            return
        if self._session.frame_index > 0:
            self.set_frame_index(self._session.frame_index - 1)
            return
        if self._session.loop:
            self.jump_last()

    def jump_first(self) -> None:
        """Jump to the first frame."""
        if self.get_active_vm() is not None:
            self.set_frame_index(0)

    def jump_last(self) -> None:
        """Jump to the last frame of the active dataset."""
        active_vm = self.get_active_vm()
        if active_vm is None:
            return
        self.set_frame_index(active_vm.get_frame_count(self._session.mode) - 1)

    def _vm_for_slot(self, slot: str) -> DatasetViewModel | None:
        if slot == "primary":
            return self._model.primary_vm
        return self._model.compare_vm

    def _resolved_spin_index_or_zero(self) -> int:
        active = self.resolve_active_selection()
        return 0 if active is None else active.spin_index

    def _clamp_state(self) -> None:
        active = self.resolve_active_selection()
        if active is None:
            self._session = replace(
                self._session,
                acquisition_index=max(0, self._session.acquisition_index),
                frame_index=max(0, self._session.frame_index),
            )
            return
        self._session = replace(
            self._session,
            acquisition_index=active.acquisition_index,
            frame_index=active.frame_index,
            selected_delta_f_hz=active.delta_f_hz,
            bookmarks_hz=self._session.normalized_bookmarks(),
        )

    def _update_timer_interval(self) -> None:
        interval_ms = max(1, int(round(1000.0 / self._session.fps)))
        self._timer.setInterval(interval_ms)

    def _emit_resolved_change(
        self,
        previous: ResolvedSelection | None,
    ) -> None:
        current = self.resolve_active_selection()
        if previous is None and current is None:
            return
        if current is None:
            return
        if previous is None or previous.acquisition_index != current.acquisition_index:
            self.acquisition_changed.emit(current.acquisition_index)
        if previous is None or previous.spin_index != current.spin_index:
            self.spin_changed.emit(current.spin_index)
        if previous is None or previous.frame_index != current.frame_index:
            self.frame_changed.emit(current.frame_index)


def _normalize_mode(mode: str) -> str:
    if mode == "steady-state":
        return "steady"
    if mode not in {"reference", "steady"}:
        msg = "mode must be 'reference' or 'steady'."
        raise ValueError(msg)
    return mode


def _other_slot(slot: str) -> str:
    return "compare" if slot == "primary" else "primary"


def _nearest_spin_index(delta_f_hz: np.ndarray, canonical_delta_f_hz: float) -> int:
    delta = np.abs(np.asarray(delta_f_hz, dtype=np.float64) - float(canonical_delta_f_hz))
    return int(np.argmin(delta))


def _clamp_frame_index(frame_count: int, index: int) -> int:
    return max(0, min(int(index), max(0, frame_count - 1)))


def _map_frame_index(index: int, na: int, nb: int) -> int:
    if na <= 1:
        ratio = 0.0
    else:
        ratio = index / float(na - 1)
    if nb <= 1:
        return 0
    return int(round(ratio * float(nb - 1)))

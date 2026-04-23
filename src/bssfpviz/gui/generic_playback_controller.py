"""Playback controller for generic animation view-models."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from bssfpviz.gui.animation_view_model import AnimationViewModel
from bssfpviz.gui.playback_controller import DEFAULT_FPS, PlaybackState


class GenericPlaybackController(QObject):
    """Small playback controller for bundle-driven generic scene rendering."""

    state_changed = Signal(object)
    frame_changed = Signal(int)
    mode_changed = Signal(str)
    acquisition_changed = Signal(int)
    spin_changed = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._vm: AnimationViewModel | None = None
        self._state = PlaybackState(
            mode="reference",
            acquisition_index=0,
            spin_index=0,
            frame_index=0,
            is_playing=False,
            loop=True,
            fps=DEFAULT_FPS,
        )
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self.step_forward)
        self._update_timer_interval()

    def set_view_model(self, vm: AnimationViewModel | None) -> None:
        """Attach one animation view-model or clear playback."""
        self.stop()
        self._vm = vm
        if vm is None:
            self._state = replace(
                self._state,
                acquisition_index=0,
                spin_index=0,
                frame_index=0,
                is_playing=False,
            )
            self.state_changed.emit(self.state())
            return
        self._state = replace(
            self._state,
            acquisition_index=min(self._state.acquisition_index, vm.n_acq - 1),
            spin_index=min(self._state.spin_index, vm.n_spins - 1),
            frame_index=min(self._state.frame_index, vm.get_frame_count(self._state.mode) - 1),
            is_playing=False,
        )
        self.state_changed.emit(self.state())

    def view_model(self) -> AnimationViewModel | None:
        """Return the active animation view-model."""
        return self._vm

    def state(self) -> PlaybackState:
        """Return a copy of the playback state."""
        return replace(self._state)

    def set_mode(self, mode: str) -> None:
        """Switch animation mode."""
        normalized = "steady" if mode == "steady-state" else mode
        if normalized not in {"reference", "steady"}:
            msg = f"Unsupported playback mode: {mode!r}"
            raise ValueError(msg)
        frame_index = self._state.frame_index
        if self._vm is not None:
            frame_index = min(frame_index, self._vm.get_frame_count(normalized) - 1)
        self._state = replace(self._state, mode=normalized, frame_index=max(0, frame_index))
        self.mode_changed.emit(normalized)
        self.frame_changed.emit(self._state.frame_index)
        self.state_changed.emit(self.state())

    def set_acquisition_index(self, index: int) -> None:
        """Set acquisition/train index."""
        if self._vm is None:
            return
        clamped = max(0, min(int(index), self._vm.n_acq - 1))
        if clamped == self._state.acquisition_index:
            return
        self._state = replace(self._state, acquisition_index=clamped)
        self.acquisition_changed.emit(clamped)
        self.state_changed.emit(self.state())

    def set_spin_index(self, index: int) -> None:
        """Set selected entity index."""
        if self._vm is None:
            return
        clamped = max(0, min(int(index), self._vm.n_spins - 1))
        if clamped == self._state.spin_index:
            return
        self._state = replace(self._state, spin_index=clamped)
        self.spin_changed.emit(clamped)
        self.state_changed.emit(self.state())

    def set_frame_index(self, index: int) -> None:
        """Set current frame index."""
        if self._vm is None:
            return
        clamped = max(0, min(int(index), self._vm.get_frame_count(self._state.mode) - 1))
        if clamped == self._state.frame_index:
            return
        self._state = replace(self._state, frame_index=clamped)
        self.frame_changed.emit(clamped)
        self.state_changed.emit(self.state())

    def set_fps(self, fps: float) -> None:
        """Update playback FPS."""
        self._state = replace(self._state, fps=max(0.1, float(fps)))
        self._update_timer_interval()
        self.state_changed.emit(self.state())

    def toggle_play(self) -> None:
        """Toggle timer-driven playback."""
        if self._vm is None:
            return
        if self._state.is_playing:
            self.stop()
            return
        self._state = replace(self._state, is_playing=True)
        self._timer.start()
        self.state_changed.emit(self.state())

    def stop(self) -> None:
        """Stop playback."""
        if self._timer.isActive():
            self._timer.stop()
        if self._state.is_playing:
            self._state = replace(self._state, is_playing=False)
            self.state_changed.emit(self.state())

    def step_forward(self) -> None:
        """Advance one frame."""
        if self._vm is None:
            return
        frame_count = self._vm.get_frame_count(self._state.mode)
        if self._state.frame_index + 1 < frame_count:
            self.set_frame_index(self._state.frame_index + 1)
        else:
            self.set_frame_index(0)

    def step_backward(self) -> None:
        """Move one frame backward."""
        if self._vm is None:
            return
        if self._state.frame_index > 0:
            self.set_frame_index(self._state.frame_index - 1)
        else:
            self.set_frame_index(self._vm.get_frame_count(self._state.mode) - 1)

    def _update_timer_interval(self) -> None:
        self._timer.setInterval(max(1, int(round(1000.0 / self._state.fps))))

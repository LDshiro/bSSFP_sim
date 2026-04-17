"""Central playback controller for synchronized 3D and 2D observation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from bssfpviz.gui.dataset_view_model import DatasetViewModel

DEFAULT_FPS = 30.0


@dataclass(slots=True)
class PlaybackState:
    """Current synchronized playback state."""

    mode: str
    acquisition_index: int
    spin_index: int
    frame_index: int
    is_playing: bool
    loop: bool
    fps: float


class PlaybackController(QObject):
    """Single source of truth for mode / acquisition / spin / frame state."""

    state_changed = Signal(object)
    frame_changed = Signal(int)
    mode_changed = Signal(str)
    acquisition_changed = Signal(int)
    spin_changed = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._vm: DatasetViewModel | None = None
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
        self._timer.timeout.connect(self._on_timeout)
        self._update_timer_interval()

    def set_dataset(self, vm: DatasetViewModel | None) -> None:
        """Attach a dataset view-model or clear playback state."""
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

        frame_index = min(self._state.frame_index, vm.get_frame_count(self._state.mode) - 1)
        self._state = replace(
            self._state,
            acquisition_index=min(self._state.acquisition_index, vm.n_acq - 1),
            spin_index=min(self._state.spin_index, vm.n_spins - 1),
            frame_index=max(0, frame_index),
            is_playing=False,
        )
        self.state_changed.emit(self.state())

    def view_model(self) -> DatasetViewModel | None:
        """Return the currently attached dataset view-model."""
        return self._vm

    def state(self) -> PlaybackState:
        """Return a copy of the current playback state."""
        return replace(self._state)

    def set_mode(self, mode: str) -> None:
        """Switch between `reference` and `steady` playback modes."""
        normalized_mode = _normalize_mode(mode)
        if self._vm is None:
            self._state = replace(self._state, mode=normalized_mode)
            self.mode_changed.emit(normalized_mode)
            self.state_changed.emit(self.state())
            return
        new_frame_count = self._vm.get_frame_count(normalized_mode)
        new_index = min(self._state.frame_index, new_frame_count - 1)
        self._state = replace(self._state, mode=normalized_mode, frame_index=max(0, new_index))
        self.mode_changed.emit(normalized_mode)
        self.frame_changed.emit(self._state.frame_index)
        self.state_changed.emit(self.state())

    def set_acquisition_index(self, index: int) -> None:
        """Update the current acquisition index."""
        if self._vm is None:
            return
        clamped = max(0, min(index, self._vm.n_acq - 1))
        if clamped == self._state.acquisition_index:
            return
        self._state = replace(self._state, acquisition_index=clamped)
        self.acquisition_changed.emit(clamped)
        self.state_changed.emit(self.state())

    def set_spin_index(self, index: int) -> None:
        """Update the selected spin index."""
        if self._vm is None:
            return
        clamped = max(0, min(index, self._vm.n_spins - 1))
        if clamped == self._state.spin_index:
            return
        self._state = replace(self._state, spin_index=clamped)
        self.spin_changed.emit(clamped)
        self.state_changed.emit(self.state())

    def set_frame_index(self, index: int) -> None:
        """Move to a specific frame in the current mode."""
        if self._vm is None:
            return
        frame_count = self._vm.get_frame_count(self._state.mode)
        clamped = max(0, min(index, frame_count - 1))
        if clamped == self._state.frame_index:
            return
        self._state = replace(self._state, frame_index=clamped)
        self.frame_changed.emit(clamped)

    def set_fps(self, fps: float) -> None:
        """Update the playback rate in frames per second."""
        clamped = max(0.1, float(fps))
        self._state = replace(self._state, fps=clamped)
        self._update_timer_interval()
        self.state_changed.emit(self.state())

    def set_loop(self, enabled: bool) -> None:
        """Enable or disable playback looping."""
        self._state = replace(self._state, loop=bool(enabled))
        self.state_changed.emit(self.state())

    def toggle_play(self) -> None:
        """Toggle the timer-driven playback state."""
        if self._vm is None:
            return
        if self._state.is_playing:
            self.stop()
            return
        self._state = replace(self._state, is_playing=True)
        self._update_timer_interval()
        self._timer.start()
        self.state_changed.emit(self.state())

    def stop(self) -> None:
        """Stop playback and keep the current frame."""
        if self._timer.isActive():
            self._timer.stop()
        if self._state.is_playing:
            self._state = replace(self._state, is_playing=False)
            self.state_changed.emit(self.state())

    def step_forward(self) -> None:
        """Advance by one frame respecting loop settings."""
        if self._vm is None:
            return
        frame_count = self._vm.get_frame_count(self._state.mode)
        if self._state.frame_index + 1 < frame_count:
            self.set_frame_index(self._state.frame_index + 1)
            return
        if self._state.loop:
            self.set_frame_index(0)
            return
        self.stop()

    def step_backward(self) -> None:
        """Move one frame backward respecting loop settings."""
        if self._vm is None:
            return
        if self._state.frame_index > 0:
            self.set_frame_index(self._state.frame_index - 1)
            return
        if self._state.loop:
            self.jump_last()

    def jump_first(self) -> None:
        """Jump to the first frame."""
        if self._vm is None:
            return
        self.set_frame_index(0)

    def jump_last(self) -> None:
        """Jump to the last frame of the current mode."""
        if self._vm is None:
            return
        self.set_frame_index(self._vm.get_frame_count(self._state.mode) - 1)

    def _on_timeout(self) -> None:
        self.step_forward()

    def _update_timer_interval(self) -> None:
        interval_ms = max(1, int(round(1000.0 / self._state.fps)))
        self._timer.setInterval(interval_ms)


def _normalize_mode(mode: str) -> str:
    if mode == "steady-state":
        return "steady"
    if mode not in {"reference", "steady"}:
        msg = f"Unsupported playback mode: {mode!r}"
        raise ValueError(msg)
    return mode

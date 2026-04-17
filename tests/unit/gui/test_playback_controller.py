"""Unit tests for the Chapter 6 playback controller."""

from __future__ import annotations

from bssfpviz.gui.dataset_view_model import DatasetViewModel
from bssfpviz.gui.playback_controller import PlaybackController


def test_playback_controller_clamps_frame_on_mode_change(
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    _ = qapp
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    controller = PlaybackController()
    controller.set_dataset(vm)
    controller.set_frame_index(vm.n_reference_frames - 1)

    controller.set_mode("steady")

    assert controller.state().mode == "steady"
    assert controller.state().frame_index == vm.n_steady_frames - 1


def test_playback_controller_steps_and_loops(
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    _ = qapp
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    controller = PlaybackController()
    controller.set_dataset(vm)
    controller.set_mode("steady")
    controller.jump_last()
    controller.set_loop(True)

    controller.step_forward()
    assert controller.state().frame_index == 0

    controller.set_loop(False)
    controller.jump_last()
    controller.toggle_play()
    controller.step_forward()

    assert controller.state().frame_index == vm.n_steady_frames - 1
    assert controller.state().is_playing is False

    controller.jump_first()
    controller.step_backward()
    assert controller.state().frame_index == 0


def test_playback_controller_is_noop_without_dataset(qapp: object) -> None:
    _ = qapp
    controller = PlaybackController()

    controller.step_forward()
    controller.step_backward()
    controller.toggle_play()
    controller.set_mode("reference")

    assert controller.state().frame_index == 0


def test_playback_controller_emits_frame_changed_on_frame_move(
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    _ = qapp
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    controller = PlaybackController()
    controller.set_dataset(vm)
    emitted_frames: list[int] = []
    state_changes: list[object] = []
    controller.frame_changed.connect(emitted_frames.append)
    controller.state_changed.connect(state_changes.append)

    controller.set_frame_index(2)

    assert emitted_frames == [2]
    assert state_changes == []

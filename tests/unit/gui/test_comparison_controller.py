"""Unit tests for the Chapter 7 comparison controller."""

from __future__ import annotations

import numpy as np

from bssfpviz.gui.comparison_controller import ComparisonController
from bssfpviz.gui.dataset_view_model import DatasetViewModel
from bssfpviz.models.config import PhysicsConfig, SamplingConfig, SequenceConfig, SimulationConfig
from conftest import build_test_simulation_dataset


def test_comparison_controller_resolves_active_selection_with_nearest_delta_f(qapp: object) -> None:
    _ = qapp
    primary_vm = DatasetViewModel.from_dataset(
        _make_dataset(delta_f_hz=np.array([-100.0, 0.0, 100.0], dtype=np.float64), n_acq=2)
    )
    controller = ComparisonController()
    controller.set_primary_dataset(primary_vm)
    controller.set_selected_delta_f_hz(7.5)

    resolved = controller.resolve_active_selection()

    assert resolved is not None
    assert resolved.slot == "primary"
    assert resolved.spin_index == 1
    assert np.isclose(resolved.delta_f_hz, 0.0)


def test_comparison_controller_resolves_other_selection_by_rules(qapp: object) -> None:
    _ = qapp
    primary_vm = DatasetViewModel.from_dataset(
        _make_dataset(
            delta_f_hz=np.array([-100.0, 0.0, 100.0], dtype=np.float64),
            n_acq=2,
            n_rf_samples=8,
            n_cycles=6,
        )
    )
    compare_vm = DatasetViewModel.from_dataset(
        _make_dataset(
            delta_f_hz=np.array([-120.0, 25.0], dtype=np.float64),
            n_acq=1,
            n_rf_samples=6,
            n_cycles=3,
        )
    )
    controller = ComparisonController()
    controller.set_primary_dataset(primary_vm)
    controller.set_compare_dataset(compare_vm)
    controller.set_compare_enabled(True)
    controller.set_mode("reference")
    controller.set_acquisition_index(1)
    controller.set_selected_delta_f_hz(8.0)
    controller.set_frame_index(primary_vm.n_reference_frames // 2)

    other = controller.resolve_other_selection()

    assert other is not None
    assert other.slot == "compare"
    assert other.acquisition_index == 0
    assert other.spin_index == 1
    expected_frame = int(
        round(
            (
                controller.resolve_active_selection().frame_index
                / float(primary_vm.n_reference_frames - 1)
            )
            * float(compare_vm.n_reference_frames - 1)
        )
    )
    assert other.frame_index == expected_frame
    assert np.isclose(other.delta_f_hz, 25.0)


def test_comparison_controller_bookmarks_are_sorted_and_deduplicated(qapp: object) -> None:
    _ = qapp
    controller = ComparisonController()
    primary_vm = DatasetViewModel.from_dataset(
        _make_dataset(delta_f_hz=np.array([-5.0, 0.0, 10.0], dtype=np.float64))
    )
    controller.set_primary_dataset(primary_vm)
    controller.add_bookmark(10.0)
    controller.add_bookmark(10.0 + 5.0e-10)
    controller.add_bookmark(-5.0)

    assert controller.session_state().bookmarks_hz == [-5.0, 10.0]

    controller.jump_to_bookmark(-5.0)
    active = controller.resolve_active_selection()
    assert active is not None
    assert active.spin_index == 0


def test_comparison_controller_emits_frame_changed_without_selection_or_state_changed(
    qapp: object,
) -> None:
    _ = qapp
    primary_vm = DatasetViewModel.from_dataset(
        _make_dataset(delta_f_hz=np.array([-10.0, 0.0, 10.0], dtype=np.float64))
    )
    controller = ComparisonController()
    controller.set_primary_dataset(primary_vm)
    emitted_frames: list[int] = []
    selection_changes: list[str] = []
    state_changes: list[str] = []
    controller.frame_changed.connect(emitted_frames.append)
    controller.selection_changed.connect(lambda: selection_changes.append("selection"))
    controller.state_changed.connect(lambda: state_changes.append("state"))

    controller.set_frame_index(2)

    assert emitted_frames == [2]
    assert selection_changes == []
    assert state_changes == []


def _make_dataset(
    *,
    delta_f_hz: np.ndarray,
    n_acq: int = 2,
    n_rf_samples: int = 8,
    n_cycles: int = 6,
) -> object:
    phase_schedule = np.zeros((n_acq, 2), dtype=np.float64)
    if n_acq > 1:
        phase_schedule[1, 1] = np.pi
    n_steady_state_steps = 2 * n_rf_samples + 3
    n_reference_steps = n_cycles * (n_steady_state_steps - 1) + 1
    config = SimulationConfig(
        physics=PhysicsConfig(t1_s=0.050, t2_s=0.025, m0=1.0),
        sequence=SequenceConfig(
            tr_s=0.004,
            te_s=0.0025,
            rf_duration_s=0.001,
            free_duration_s=0.003,
            n_rf_samples=n_rf_samples,
            flip_angle_rad=float(np.pi / 4.0),
            phase_schedule_rad=phase_schedule,
            n_cycles=n_cycles,
        ),
        sampling=SamplingConfig(
            delta_f_hz=np.asarray(delta_f_hz, dtype=np.float64),
            rk_dt_s=2.0e-5,
            steady_state_dt_s=2.0e-5,
            n_reference_steps=n_reference_steps,
            n_steady_state_steps=n_steady_state_steps,
        ),
    )
    return build_test_simulation_dataset(config)

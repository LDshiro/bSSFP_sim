"""Unit tests for the Chapter 6 profile panel."""

from __future__ import annotations

import numpy as np

from bssfpviz.gui.comparison_controller import ComparisonController
from bssfpviz.gui.dataset_view_model import DatasetViewModel
from bssfpviz.gui.playback_controller import PlaybackController
from bssfpviz.gui.profile_panel import ProfilePanel
from conftest import build_test_simulation_config, build_test_simulation_dataset


def test_profile_panel_prepares_profile_curves(
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    controller = PlaybackController()
    controller.set_dataset(vm)
    panel = ProfilePanel()
    panel.set_controller(controller)
    panel.set_dataset(vm)
    qapp.processEvents()

    assert panel._last_curve_count == vm.n_acq + 1
    assert panel.profile_plot.getPlotItem().listDataItems()
    assert len(panel.transverse_signal_plot.getPlotItem().listDataItems()) == 1


def test_profile_panel_updates_markers_on_spin_and_frame_change(
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    controller = PlaybackController()
    controller.set_dataset(vm)
    panel = ProfilePanel()
    panel.set_controller(controller)
    panel.set_dataset(vm)
    qapp.processEvents()

    initial_profile_curve_count = len(panel.profile_plot.getPlotItem().listDataItems())
    initial_time_curve_count = len(panel.time_series_plot.getPlotItem().listDataItems())
    initial_transverse_curve_count = len(panel.transverse_signal_plot.getPlotItem().listDataItems())

    controller.set_spin_index(1)
    qapp.processEvents()
    assert np.isclose(panel._profile_marker_x, vm.get_selected_delta_f_hz(1))

    controller.set_frame_index(3)
    qapp.processEvents()
    expected_time = vm.get_current_time_s(controller.state().mode, 3)
    assert np.isclose(panel._time_marker_x, expected_time)
    assert len(panel.profile_plot.getPlotItem().listDataItems()) == initial_profile_curve_count
    assert len(panel.time_series_plot.getPlotItem().listDataItems()) == initial_time_curve_count
    assert (
        len(panel.transverse_signal_plot.getPlotItem().listDataItems())
        == initial_transverse_curve_count
    )


def test_profile_panel_renders_compare_overlay(
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    primary_vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    compare_dataset = build_test_simulation_dataset(
        build_test_simulation_config(
            n_rf_samples=6,
            n_cycles=4,
            delta_f_hz=np.array([-12.0, 5.0, 30.0], dtype=np.float64),
        )
    )
    compare_vm = DatasetViewModel.from_dataset(compare_dataset)
    controller = ComparisonController()
    controller.set_primary_dataset(primary_vm)
    controller.set_compare_dataset(compare_vm)
    controller.set_compare_enabled(True)
    controller.set_selected_delta_f_hz(4.0)
    panel = ProfilePanel()
    panel.set_controller(controller)
    qapp.processEvents()

    assert panel._compare_marker_x is not None
    controller.set_frame_index(2)
    qapp.processEvents()

    assert panel._compare_time_marker_x is not None
    assert len(panel.transverse_signal_plot.getPlotItem().listDataItems()) == 2

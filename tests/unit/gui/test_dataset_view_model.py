"""Unit tests for the Chapter 6 dataset view-model."""

from __future__ import annotations

import numpy as np

from bssfpviz.gui.dataset_view_model import DatasetViewModel


def test_dataset_view_model_reports_mode_specific_frame_counts(
    small_simulation_dataset: object,
) -> None:
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)

    assert vm.get_frame_count("reference") == vm.n_reference_frames
    assert vm.get_frame_count("steady") == vm.n_steady_frames
    assert vm.get_frame_count("steady-state") == vm.n_steady_frames


def test_dataset_view_model_returns_vectors_and_series_with_expected_shapes(
    small_simulation_dataset: object,
) -> None:
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)

    vectors = vm.get_vectors_xyz("reference", acquisition_index=0, frame_index=0)
    series = vm.get_spin_series_xyz("steady", acquisition_index=1, spin_index=2)

    assert vectors.shape == (vm.n_spins, 3)
    assert series.shape == (vm.n_steady_frames, 3)


def test_dataset_view_model_returns_selected_delta_f(small_simulation_dataset: object) -> None:
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)

    selected = vm.get_selected_delta_f_hz(1)

    assert np.isclose(selected, vm.delta_f_hz[1])

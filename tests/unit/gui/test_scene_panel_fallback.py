"""Fallback-only tests for the Chapter 6 scene panel."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from bssfpviz.gui.comparison_controller import ComparisonController
from bssfpviz.gui.dataset_view_model import DatasetViewModel
from bssfpviz.gui.playback_controller import PlaybackController
from bssfpviz.gui.scene_panel import ScenePanel


def test_scene_panel_fallback_updates_text(
    monkeypatch: object,
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    controller = PlaybackController()
    controller.set_dataset(vm)
    panel = ScenePanel()
    panel.set_controller(controller)
    panel.set_dataset(vm)

    assert panel._placeholder_label is not None
    assert "dataset loaded" in panel._placeholder_label.text()

    controller.set_frame_index(2)
    controller.set_spin_index(1)
    panel.refresh_scene()

    text = panel._placeholder_label.text()
    assert "frame:" in text
    assert "spin: 1" in text


def test_scene_panel_fallback_renders_comparison_state(
    monkeypatch: object,
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    primary_vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    compare_vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    controller = ComparisonController()
    controller.set_primary_dataset(primary_vm)
    controller.set_compare_dataset(compare_vm)
    controller.set_compare_enabled(True)
    controller.set_selected_delta_f_hz(primary_vm.get_selected_delta_f_hz(1))

    panel = ScenePanel()
    panel.set_controller(controller)
    qapp.processEvents()

    assert panel._placeholder_label is not None
    text = panel._placeholder_label.text()
    assert "compare spin:" in text


def test_scene_panel_reuses_cached_geometry_on_frame_changes(
    monkeypatch: object,
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    controller = PlaybackController()
    controller.set_dataset(vm)
    panel = ScenePanel()
    panel._mode = "pyvista"
    panel._plotter = _FakePlotter()
    panel._pyvista = _FakePyVista()
    panel._placeholder_label = None
    panel._base_ready = False
    panel.set_dataset(vm)
    panel.set_controller(controller)

    initial_mesh_calls = panel._plotter.add_mesh_calls
    initial_text_calls = panel._plotter.add_text_calls
    initial_orbit_cache_size = len(panel._orbit_cache)
    initial_active_points = panel._active_vectors_mesh.points.copy()
    initial_selected_points = panel._selected_vector_mesh.points.copy()

    controller.set_frame_index(2)

    expected_vectors = vm.get_vectors_xyz("reference", 0, 2)
    assert panel._plotter.add_mesh_calls == initial_mesh_calls
    assert initial_text_calls == 0
    assert panel._plotter.add_text_calls == initial_text_calls
    assert len(panel._orbit_cache) == initial_orbit_cache_size
    assert not np.allclose(panel._active_vectors_mesh.points, initial_active_points)
    assert not np.allclose(panel._selected_vector_mesh.points, initial_selected_points)
    assert np.allclose(
        panel._active_vectors_mesh.points,
        _expected_segment_points(expected_vectors),
    )
    assert np.allclose(
        panel._selected_vector_mesh.points,
        np.asarray([[0.0, 0.0, 0.0], expected_vectors[0]], dtype=np.float64),
    )
    assert not any(
        isinstance(mesh, dict)
        and mesh.get("kind") == "sphere"
        and kwargs.get("color") == "#111111"
        for mesh, kwargs in panel._plotter.added_meshes
    )


def test_scene_panel_updates_selected_geometry_on_spin_changes(
    monkeypatch: object,
    qapp: object,
    small_simulation_dataset: object,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    vm = DatasetViewModel.from_dataset(small_simulation_dataset)
    controller = ComparisonController()
    controller.set_primary_dataset(vm)
    panel = ScenePanel()
    panel._mode = "pyvista"
    panel._plotter = _FakePlotter()
    panel._pyvista = _FakePyVista()
    panel._placeholder_label = None
    panel._base_ready = False
    panel.set_controller(controller)

    assert panel._selected_vector_mesh is not None
    assert panel._selected_orbit_mesh is not None
    selected_vector_mesh = panel._selected_vector_mesh
    selected_orbit_mesh = panel._selected_orbit_mesh

    controller.set_spin_index(1)

    expected_vector = vm.get_vectors_xyz("reference", 0, 0)[1]
    expected_orbit = vm.get_steady_orbit_xyz(0)[1]
    assert panel._selected_vector_mesh is selected_vector_mesh
    assert panel._selected_orbit_mesh is selected_orbit_mesh
    assert np.allclose(
        panel._selected_vector_mesh.points,
        np.asarray([[0.0, 0.0, 0.0], expected_vector], dtype=np.float64),
    )
    assert np.allclose(panel._selected_orbit_mesh.points, expected_orbit)
    assert not any(
        isinstance(mesh, dict)
        and mesh.get("kind") == "sphere"
        and kwargs.get("color") == "#111111"
        for mesh, kwargs in panel._plotter.added_meshes
    )


@dataclass
class _FakeActor:
    visible: bool = True
    text: str | None = None

    def SetVisibility(self, visible: bool) -> None:
        self.visible = bool(visible)

    def SetInput(self, text: str) -> None:
        self.text = text


class _FakeVTKPoints:
    def __init__(self) -> None:
        self.modified_calls = 0

    def Modified(self) -> None:
        self.modified_calls += 1


class _FakePolyData:
    def __init__(self) -> None:
        self._points = np.zeros((0, 3), dtype=np.float64)
        self._lines = np.zeros((0,), dtype=np.int32)
        self.modified_calls = 0
        self._vtk_points = _FakeVTKPoints()

    @property
    def points(self) -> np.ndarray:
        return self._points.copy()

    @points.setter
    def points(self, value: np.ndarray) -> None:
        self._points = np.asarray(value, dtype=np.float64).copy()

    @property
    def lines(self) -> np.ndarray:
        return self._lines.copy()

    @lines.setter
    def lines(self, value: np.ndarray) -> None:
        self._lines = np.asarray(value, dtype=np.int32).copy()

    def GetPoints(self) -> _FakeVTKPoints:
        return self._vtk_points

    def Modified(self) -> None:
        self.modified_calls += 1


class _FakePyVista:
    @staticmethod
    def Sphere(*_args: object, **_kwargs: object) -> object:
        return {"kind": "sphere"}

    @staticmethod
    def Line(start: tuple[float, float, float], end: tuple[float, float, float]) -> object:
        return {"kind": "line", "start": start, "end": end}

    PolyData = _FakePolyData


class _FakePlotter:
    def __init__(self) -> None:
        self.add_mesh_calls = 0
        self.add_text_calls = 0
        self.added_meshes: list[tuple[object, dict[str, object]]] = []

    def clear(self) -> None:
        return

    def set_background(self, _color: str) -> None:
        return

    def add_axes(self) -> None:
        return

    def add_mesh(self, _mesh: object, **_kwargs: object) -> _FakeActor:
        self.add_mesh_calls += 1
        self.added_meshes.append((_mesh, dict(_kwargs)))
        return _FakeActor()

    def add_text(self, text: str, **_kwargs: object) -> _FakeActor:
        self.add_text_calls += 1
        return _FakeActor(text=text)

    def remove_actor(self, _actor: object) -> None:
        return

    def render(self) -> None:
        return

    def reset_camera(self) -> None:
        return


def _expected_segment_points(vectors_xyz: np.ndarray) -> np.ndarray:
    points = np.zeros((vectors_xyz.shape[0] * 2, 3), dtype=np.float64)
    points[1::2] = vectors_xyz
    return points

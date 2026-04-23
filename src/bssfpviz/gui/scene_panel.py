"""3D Bloch scene panel with cached geometry for fast playback updates."""

from __future__ import annotations

import os
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from bssfpviz.gui.comparison_controller import ComparisonController, ResolvedSelection
from bssfpviz.gui.dataset_view_model import DatasetViewModel
from bssfpviz.gui.playback_controller import PlaybackController, PlaybackState

ACTIVE_VECTOR_COLOR = "#2a6fdb"
ACTIVE_SELECTED_VECTOR_COLOR = "#0b3d91"
ACTIVE_ORBIT_COLOR = "#2f9e44"
COMPARE_VECTOR_COLOR = "#f08c00"
COMPARE_ORBIT_COLOR = "#c92a2a"
DEFAULT_ACTIVE_VECTOR_LINE_WIDTH = 1
THICK_ACTIVE_VECTOR_LINE_WIDTH = 4
ACTIVE_SELECTED_VECTOR_LINE_WIDTH = 5
DEFAULT_ACTIVE_ORBIT_LINE_WIDTH = 1
THICK_ACTIVE_ORBIT_LINE_WIDTH = 3
ACTIVE_SELECTED_ORBIT_LINE_WIDTH = 4
COMPARE_VECTOR_LINE_WIDTH = 5
COMPARE_ORBIT_LINE_WIDTH = 3


@dataclass(slots=True)
class _OrbitCacheEntry:
    mesh: Any
    actor: Any


@dataclass(slots=True)
class _SceneSelectionState:
    active_vm_id: int
    active_acquisition_index: int
    active_spin_index: int
    active_slot: str
    mode: str
    compare_vm_id: int | None
    compare_acquisition_index: int | None
    compare_spin_index: int | None


class ScenePanel(QWidget):
    """Display Bloch vectors in 3D or a textual fallback."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm: Any | None = None
        self._controller: Any | None = None
        self._mode = "fallback"
        self._plotter: Any | None = None
        self._pyvista: Any | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder_label: QLabel | None = None
        self._base_ready = False
        self._orbit_cache: dict[tuple[int, int], _OrbitCacheEntry] = {}
        self._loaded_vm_ids: set[int] = set()
        self._render_state: _SceneSelectionState | None = None
        self._active_vectors_mesh: Any | None = None
        self._active_vectors_actor: Any | None = None
        self._selected_vector_mesh: Any | None = None
        self._selected_vector_actor: Any | None = None
        self._compare_vector_mesh: Any | None = None
        self._compare_vector_actor: Any | None = None
        self._selected_orbit_mesh: Any | None = None
        self._selected_orbit_actor: Any | None = None
        self._compare_orbit_mesh: Any | None = None
        self._compare_orbit_actor: Any | None = None
        self._initialize_backend()

    def set_dataset(self, vm: DatasetViewModel | None) -> None:
        """Attach a single dataset view-model for Chapter 6 compatible rendering."""
        if self._vm is not vm:
            self._vm = vm
            self._clear_cached_scene()
        self.refresh_scene()

    def set_controller(
        self,
        controller: PlaybackController | ComparisonController | None,
    ) -> None:
        """Attach a playback-like controller and follow its state."""
        if self._controller is controller:
            self.refresh_scene()
            return

        self._disconnect_controller_signals()
        self._controller = controller
        self._connect_controller_signals(controller)
        if isinstance(controller, ComparisonController):
            self.render_from_comparison_controller(controller)
        else:
            self.refresh_scene()

    def set_generic_controller(self, controller: Any | None) -> None:
        """Attach a generic playback controller while reusing the optimized renderer."""
        if self._controller is controller:
            self._vm = None if controller is None else controller.view_model()
            self.refresh_scene()
            return

        self._disconnect_controller_signals()
        self._controller = controller
        self._vm = None if controller is None else controller.view_model()
        self._connect_controller_signals(controller)
        self.refresh_scene()

    def refresh_scene(self) -> None:
        """Refresh the scene from the currently attached single dataset."""
        if self._vm is None:
            self._render_fallback_text("No dataset loaded")
            return

        state = self._state()
        if state is None:
            self._render_fallback_text("No dataset loaded")
            return

        active = ResolvedSelection(
            slot="primary",
            acquisition_index=min(state.acquisition_index, self._vm.n_acq - 1),
            spin_index=min(state.spin_index, self._vm.n_spins - 1),
            frame_index=min(state.frame_index, self._vm.get_frame_count(state.mode) - 1),
            delta_f_hz=self._vm.get_selected_delta_f_hz(state.spin_index),
        )
        self._apply_scene_state(
            active_vm=self._vm,
            active_selection=active,
            mode=state.mode,
            compare_vm=None,
            compare_selection=None,
            frame_only=False,
        )

    def render_from_comparison_controller(self, controller: ComparisonController) -> None:
        """Render active and compare data using Chapter 7 selection rules."""
        active_vm = controller.get_active_vm()
        active_selection = controller.resolve_active_selection()
        compare_vm = controller.get_other_vm()
        compare_selection = controller.resolve_other_selection()

        if active_vm is None or active_selection is None:
            self._render_fallback_text("No dataset loaded")
            return

        if not controller.session_state().compare_visible_in_scene:
            compare_vm = None
            compare_selection = None

        self._apply_scene_state(
            active_vm=active_vm,
            active_selection=active_selection,
            mode=controller.session_state().mode,
            compare_vm=compare_vm,
            compare_selection=compare_selection,
            frame_only=False,
        )

    def reset_camera(self) -> None:
        """Reset the 3D camera when a live backend is available."""
        if self._mode == "pyvista" and self._plotter is not None:
            self._plotter.reset_camera()

    def reset_view(self) -> None:
        """Compatibility alias for older wiring."""
        self.reset_camera()

    def clear_scene(self) -> None:
        """Clear cached render state and restore the static base scene."""
        self._clear_cached_scene()
        if self._mode != "pyvista" or self._plotter is None:
            self._render_fallback_text("3D scene unavailable")
            return
        self._ensure_base_scene()
        self._plotter.render()

    def show_placeholder(self, text: str = "No dataset loaded") -> None:
        """Show a placeholder message in either backend mode."""
        self._render_fallback_text(text)

    def save_screenshot(self, path: Path) -> None:
        """Save a screenshot of the scene panel."""
        path.parent.mkdir(parents=True, exist_ok=True)
        if self._mode == "pyvista" and self._plotter is not None:
            try:
                self._plotter.screenshot(str(path))
                return
            except Exception:  # noqa: BLE001
                pass
        self.grab().save(str(path))

    def _disconnect_controller_signals(self) -> None:
        if self._controller is None:
            return
        signal_names = [
            "frame_changed",
            "mode_changed",
            "acquisition_changed",
            "spin_changed",
            "selection_changed",
            "datasets_changed",
        ]
        for signal_name in signal_names:
            signal = getattr(self._controller, signal_name, None)
            if signal is None:
                continue
            handler = (
                self._handle_frame_changed
                if signal_name == "frame_changed"
                else self._handle_structure_changed
            )
            with suppress(TypeError):
                signal.disconnect(handler)

    def _connect_controller_signals(
        self,
        controller: PlaybackController | ComparisonController | None,
    ) -> None:
        if controller is None:
            return
        controller.frame_changed.connect(self._handle_frame_changed)
        controller.mode_changed.connect(self._handle_structure_changed)
        controller.acquisition_changed.connect(self._handle_structure_changed)
        controller.spin_changed.connect(self._handle_structure_changed)
        if isinstance(controller, ComparisonController):
            controller.selection_changed.connect(self._handle_structure_changed)
            controller.datasets_changed.connect(self._handle_structure_changed)

    def _initialize_backend(self) -> None:
        if os.environ.get("BSSFPVIZ_DISABLE_3D") == "1":
            self._install_placeholder()
            return
        try:
            import pyvista as pv
            from pyvistaqt import QtInteractor

            plotter = QtInteractor(self)
            self._layout.addWidget(plotter)
            self._mode = "pyvista"
            self._plotter = plotter
            self._pyvista = pv
            self._ensure_base_scene()
        except Exception:  # noqa: BLE001
            self._install_placeholder()

    def _install_placeholder(self) -> None:
        self._mode = "fallback"
        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        self._placeholder_label = QLabel("3D scene unavailable", frame)
        self._placeholder_label.setObjectName("scene-placeholder-label")
        self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder_label.setWordWrap(True)
        layout.addWidget(self._placeholder_label)
        self._layout.addWidget(frame)

    def _ensure_base_scene(self) -> None:
        if self._mode != "pyvista" or self._plotter is None or self._pyvista is None:
            return
        if self._base_ready:
            return
        self._plotter.clear()
        self._plotter.set_background("white")
        self._plotter.add_axes()
        sphere = self._pyvista.Sphere(radius=1.0, theta_resolution=36, phi_resolution=36)
        self._plotter.add_mesh(
            sphere,
            color="lightgray",
            style="wireframe",
            opacity=0.35,
            line_width=1,
        )
        self._plotter.add_mesh(
            self._pyvista.Line((-1.2, 0.0, 0.0), (1.2, 0.0, 0.0)),
            color="#d1495b",
            line_width=2,
        )
        self._plotter.add_mesh(
            self._pyvista.Line((0.0, -1.2, 0.0), (0.0, 1.2, 0.0)),
            color="#00798c",
            line_width=2,
        )
        self._plotter.add_mesh(
            self._pyvista.Line((0.0, 0.0, -1.2), (0.0, 0.0, 1.2)),
            color="#30638e",
            line_width=2,
        )
        self._base_ready = True

    def _apply_scene_state(
        self,
        *,
        active_vm: DatasetViewModel,
        active_selection: ResolvedSelection,
        mode: str,
        compare_vm: DatasetViewModel | None,
        compare_selection: ResolvedSelection | None,
        frame_only: bool,
    ) -> None:
        if self._mode != "pyvista" or self._plotter is None or self._pyvista is None:
            self._render_comparison_fallback(
                active_vm,
                active_selection,
                mode,
                compare_vm,
                compare_selection,
            )
            return

        current_vm_ids = {id(active_vm)}
        if compare_vm is not None:
            current_vm_ids.add(id(compare_vm))
        if current_vm_ids != self._loaded_vm_ids:
            self._clear_cached_scene()
            self._loaded_vm_ids = current_vm_ids

        self._ensure_base_scene()
        emphasize_all_spins = self._thick_all_spins_enabled()
        if not frame_only or self._requires_static_refresh(
            active_vm,
            active_selection,
            mode,
            compare_vm,
            compare_selection,
        ):
            self._update_static_scene(
                active_vm,
                active_selection,
                compare_vm,
                compare_selection,
                emphasize_all_spins=emphasize_all_spins,
            )
        self._update_frame_scene(
            active_vm,
            active_selection,
            mode,
            compare_vm,
            compare_selection,
            emphasize_all_spins=emphasize_all_spins,
        )
        self._render_state = _SceneSelectionState(
            active_vm_id=id(active_vm),
            active_acquisition_index=active_selection.acquisition_index,
            active_spin_index=active_selection.spin_index,
            active_slot=active_selection.slot,
            mode=mode,
            compare_vm_id=None if compare_vm is None else id(compare_vm),
            compare_acquisition_index=(
                None if compare_selection is None else compare_selection.acquisition_index
            ),
            compare_spin_index=None if compare_selection is None else compare_selection.spin_index,
        )

    def _requires_static_refresh(
        self,
        active_vm: DatasetViewModel,
        active_selection: ResolvedSelection,
        mode: str,
        compare_vm: DatasetViewModel | None,
        compare_selection: ResolvedSelection | None,
    ) -> bool:
        if self._render_state is None:
            return True
        state = self._render_state
        return (
            state.active_vm_id != id(active_vm)
            or state.active_acquisition_index != active_selection.acquisition_index
            or state.active_spin_index != active_selection.spin_index
            or state.active_slot != active_selection.slot
            or state.compare_vm_id != (None if compare_vm is None else id(compare_vm))
            or state.compare_acquisition_index
            != (None if compare_selection is None else compare_selection.acquisition_index)
            or state.compare_spin_index
            != (None if compare_selection is None else compare_selection.spin_index)
        )

    def _update_static_scene(
        self,
        active_vm: DatasetViewModel,
        active_selection: ResolvedSelection,
        compare_vm: DatasetViewModel | None,
        compare_selection: ResolvedSelection | None,
        *,
        emphasize_all_spins: bool,
    ) -> None:
        self._show_active_orbit(
            active_vm,
            active_selection,
            emphasize_all_spins=emphasize_all_spins,
        )
        self._update_selected_active_orbit(
            active_vm,
            active_selection,
            emphasize_all_spins=emphasize_all_spins,
        )
        self._update_compare_orbit(
            compare_vm,
            compare_selection,
            emphasize_all_spins=emphasize_all_spins,
        )

    def _update_frame_scene(
        self,
        active_vm: DatasetViewModel,
        active_selection: ResolvedSelection,
        mode: str,
        compare_vm: DatasetViewModel | None,
        compare_selection: ResolvedSelection | None,
        *,
        emphasize_all_spins: bool,
    ) -> None:
        self._update_active_vectors(
            active_vm,
            active_selection,
            mode,
            emphasize_all_spins=emphasize_all_spins,
        )
        self._update_compare_vector(
            compare_vm,
            compare_selection,
            mode,
            emphasize_all_spins=emphasize_all_spins,
        )
        if self._plotter is not None:
            self._plotter.render()

    def _show_active_orbit(
        self,
        vm: DatasetViewModel,
        selection: ResolvedSelection,
        *,
        emphasize_all_spins: bool,
    ) -> None:
        if self._plotter is None or self._pyvista is None:
            return
        key = (id(vm), selection.acquisition_index)
        entry = self._orbit_cache.get(key)
        if entry is None:
            mesh = _make_multiline_mesh(
                self._pyvista, vm.get_steady_orbit_xyz(selection.acquisition_index)
            )
            actor = self._plotter.add_mesh(
                mesh,
                color=ACTIVE_ORBIT_COLOR,
                line_width=_active_orbit_line_width(emphasize_all_spins),
                opacity=0.22,
                lighting=False,
            )
            entry = _OrbitCacheEntry(mesh=mesh, actor=actor)
            self._orbit_cache[key] = entry

        for cached_key, cached_entry in self._orbit_cache.items():
            _set_actor_visibility(cached_entry.actor, cached_key == key)
            _set_actor_line_width(
                cached_entry.actor,
                _active_orbit_line_width(emphasize_all_spins),
            )

    def _update_selected_active_orbit(
        self,
        vm: DatasetViewModel,
        selection: ResolvedSelection,
        *,
        emphasize_all_spins: bool,
    ) -> None:
        if self._plotter is None or self._pyvista is None:
            return
        points = vm.get_steady_orbit_xyz(selection.acquisition_index)[selection.spin_index]
        if self._selected_orbit_mesh is None:
            self._selected_orbit_mesh = _make_polyline_mesh(self._pyvista, points)
            self._selected_orbit_actor = self._plotter.add_mesh(
                self._selected_orbit_mesh,
                color=ACTIVE_ORBIT_COLOR,
                line_width=_selected_active_orbit_line_width(emphasize_all_spins),
                opacity=0.95,
                lighting=False,
            )
            return

        _update_polyline_mesh(self._selected_orbit_mesh, points)
        _set_actor_visibility(self._selected_orbit_actor, True)
        _set_actor_line_width(
            self._selected_orbit_actor,
            _selected_active_orbit_line_width(emphasize_all_spins),
        )

    def _update_compare_orbit(
        self,
        vm: DatasetViewModel | None,
        selection: ResolvedSelection | None,
        *,
        emphasize_all_spins: bool,
    ) -> None:
        if self._plotter is None or self._pyvista is None:
            return
        if vm is None or selection is None:
            _set_actor_visibility(self._compare_orbit_actor, False)
            return

        points = vm.get_steady_orbit_xyz(selection.acquisition_index)[selection.spin_index]
        if self._compare_orbit_mesh is None:
            self._compare_orbit_mesh = _make_polyline_mesh(self._pyvista, points)
            self._compare_orbit_actor = self._plotter.add_mesh(
                self._compare_orbit_mesh,
                color=COMPARE_ORBIT_COLOR,
                line_width=_compare_orbit_line_width(emphasize_all_spins),
                opacity=0.95,
                lighting=False,
            )
            return

        _update_polyline_mesh(self._compare_orbit_mesh, points)
        _set_actor_visibility(self._compare_orbit_actor, True)
        _set_actor_line_width(
            self._compare_orbit_actor,
            _compare_orbit_line_width(emphasize_all_spins),
        )

    def _update_active_vectors(
        self,
        vm: DatasetViewModel,
        selection: ResolvedSelection,
        mode: str,
        *,
        emphasize_all_spins: bool,
    ) -> None:
        if self._plotter is None or self._pyvista is None:
            return
        vectors_xyz = vm.get_vectors_xyz(mode, selection.acquisition_index, selection.frame_index)
        if self._active_vectors_mesh is None:
            self._active_vectors_mesh = _make_segment_mesh(self._pyvista, vectors_xyz)
            self._active_vectors_actor = self._plotter.add_mesh(
                self._active_vectors_mesh,
                color=ACTIVE_VECTOR_COLOR,
                line_width=_active_vector_line_width(emphasize_all_spins),
                opacity=0.65,
                lighting=False,
            )
        else:
            _update_segment_mesh(self._active_vectors_mesh, vectors_xyz)
            _set_actor_visibility(self._active_vectors_actor, True)
            _set_actor_line_width(
                self._active_vectors_actor,
                _active_vector_line_width(emphasize_all_spins),
            )

        selected_vector = np.asarray(vectors_xyz[selection.spin_index], dtype=np.float64)
        if self._selected_vector_mesh is None:
            self._selected_vector_mesh = _make_single_segment_mesh(self._pyvista, selected_vector)
            self._selected_vector_actor = self._plotter.add_mesh(
                self._selected_vector_mesh,
                color=ACTIVE_SELECTED_VECTOR_COLOR,
                line_width=_selected_active_vector_line_width(emphasize_all_spins),
                opacity=1.0,
                lighting=False,
            )
            return

        _update_single_segment_mesh(self._selected_vector_mesh, selected_vector)
        _set_actor_visibility(self._selected_vector_actor, True)
        _set_actor_line_width(
            self._selected_vector_actor,
            _selected_active_vector_line_width(emphasize_all_spins),
        )

    def _update_compare_vector(
        self,
        vm: DatasetViewModel | None,
        selection: ResolvedSelection | None,
        mode: str,
        *,
        emphasize_all_spins: bool,
    ) -> None:
        if self._plotter is None or self._pyvista is None:
            return
        if vm is None or selection is None:
            _set_actor_visibility(self._compare_vector_actor, False)
            return

        vector_xyz = vm.get_vectors_xyz(mode, selection.acquisition_index, selection.frame_index)[
            selection.spin_index
        ]
        if self._compare_vector_mesh is None:
            self._compare_vector_mesh = _make_single_segment_mesh(self._pyvista, vector_xyz)
            self._compare_vector_actor = self._plotter.add_mesh(
                self._compare_vector_mesh,
                color=COMPARE_VECTOR_COLOR,
                line_width=_compare_vector_line_width(emphasize_all_spins),
                opacity=1.0,
                lighting=False,
            )
            return

        _update_single_segment_mesh(self._compare_vector_mesh, vector_xyz)
        _set_actor_visibility(self._compare_vector_actor, True)
        _set_actor_line_width(
            self._compare_vector_actor,
            _compare_vector_line_width(emphasize_all_spins),
        )

    def _render_fallback_text(self, text: str) -> None:
        if self._mode == "pyvista" and self._plotter is not None:
            self._ensure_base_scene()
            self._plotter.render()
            return
        if self._placeholder_label is not None:
            self._placeholder_label.setText(text)

    def _render_comparison_fallback(
        self,
        active_vm: DatasetViewModel,
        active_selection: ResolvedSelection,
        mode: str,
        compare_vm: DatasetViewModel | None,
        compare_selection: ResolvedSelection | None,
    ) -> None:
        if self._placeholder_label is None:
            return
        lines = _comparison_text_lines(active_vm, active_selection, mode, compare_selection)
        lines.insert(0, "3D scene unavailable")
        lines.insert(1, "dataset loaded")
        if compare_vm is None or compare_selection is None:
            lines.append("compare: disabled")
        self._placeholder_label.setText("\n".join(lines))

    def _clear_cached_scene(self) -> None:
        self._render_state = None
        self._loaded_vm_ids = set()
        if self._mode != "pyvista":
            return
        for entry in self._orbit_cache.values():
            self._remove_actor(entry.actor)
        self._orbit_cache = {}

        actor_names = [
            "_active_vectors_actor",
            "_selected_vector_actor",
            "_compare_vector_actor",
            "_selected_orbit_actor",
            "_compare_orbit_actor",
        ]
        for actor_name in actor_names:
            actor = getattr(self, actor_name)
            if actor is not None:
                self._remove_actor(actor)
                setattr(self, actor_name, None)

        self._active_vectors_mesh = None
        self._selected_vector_mesh = None
        self._compare_vector_mesh = None
        self._selected_orbit_mesh = None
        self._compare_orbit_mesh = None
        self._base_ready = False

    def _remove_actor(self, actor: Any) -> None:
        if actor is None or self._plotter is None:
            return
        with suppress(Exception):
            self._plotter.remove_actor(actor)

    def _state(self) -> PlaybackState | None:
        if self._controller is not None:
            return self._controller.state()
        if self._vm is None:
            return None
        return PlaybackState(
            mode="reference",
            acquisition_index=0,
            spin_index=0,
            frame_index=0,
            is_playing=False,
            loop=True,
            fps=30.0,
        )

    def _thick_all_spins_enabled(self) -> bool:
        if isinstance(self._controller, ComparisonController):
            return self._controller.session_state().thick_all_spins_in_scene
        return False

    def _handle_frame_changed(self, *_args: object) -> None:
        if isinstance(self._controller, ComparisonController):
            active_vm = self._controller.get_active_vm()
            active_selection = self._controller.resolve_active_selection()
            if active_vm is None or active_selection is None:
                self._render_fallback_text("No dataset loaded")
                return
            compare_vm = self._controller.get_other_vm()
            compare_selection = self._controller.resolve_other_selection()
            if not self._controller.session_state().compare_visible_in_scene:
                compare_vm = None
                compare_selection = None
            self._apply_scene_state(
                active_vm=active_vm,
                active_selection=active_selection,
                mode=self._controller.session_state().mode,
                compare_vm=compare_vm,
                compare_selection=compare_selection,
                frame_only=True,
            )
            return
        if self._vm is None:
            self._render_fallback_text("No dataset loaded")
            return
        state = self._state()
        if state is None:
            self._render_fallback_text("No dataset loaded")
            return
        active = ResolvedSelection(
            slot="primary",
            acquisition_index=min(state.acquisition_index, self._vm.n_acq - 1),
            spin_index=min(state.spin_index, self._vm.n_spins - 1),
            frame_index=min(state.frame_index, self._vm.get_frame_count(state.mode) - 1),
            delta_f_hz=self._vm.get_selected_delta_f_hz(state.spin_index),
        )
        self._apply_scene_state(
            active_vm=self._vm,
            active_selection=active,
            mode=state.mode,
            compare_vm=None,
            compare_selection=None,
            frame_only=True,
        )

    def _handle_structure_changed(self, *_args: object) -> None:
        if isinstance(self._controller, ComparisonController):
            self.render_from_comparison_controller(self._controller)
            return
        if self._controller is not None and not isinstance(self._controller, PlaybackController):
            self._vm = self._controller.view_model()
        self.refresh_scene()


def _make_segment_mesh(pyvista_module: Any, vectors_xyz: np.ndarray) -> Any:
    vectors = np.asarray(vectors_xyz, dtype=np.float64)
    points = _segment_points(vectors)
    lines = _segment_lines(vectors.shape[0])
    mesh = pyvista_module.PolyData()
    mesh.points = points
    mesh.lines = lines
    return mesh


def _update_segment_mesh(mesh: Any, vectors_xyz: np.ndarray) -> None:
    vectors = np.asarray(vectors_xyz, dtype=np.float64)
    points = _segment_points(vectors)
    current_shape = _mesh_points_shape(mesh)
    lines = None if current_shape == points.shape else _segment_lines(vectors.shape[0])
    _set_mesh_geometry(mesh, points, lines=lines)


def _make_single_segment_mesh(pyvista_module: Any, vector_xyz: np.ndarray) -> Any:
    return _make_polyline_mesh(pyvista_module, np.asarray([[0.0, 0.0, 0.0], vector_xyz]))


def _update_single_segment_mesh(mesh: Any, vector_xyz: np.ndarray) -> None:
    vector = np.asarray(vector_xyz, dtype=np.float64)
    _update_polyline_mesh(mesh, np.asarray([[0.0, 0.0, 0.0], vector], dtype=np.float64))


def _make_multiline_mesh(pyvista_module: Any, orbits_xyz: np.ndarray) -> Any:
    points_list: list[np.ndarray] = []
    lines_list: list[np.ndarray] = []
    offset = 0
    for orbit_xyz in np.asarray(orbits_xyz, dtype=np.float64):
        if orbit_xyz.shape[0] < 2:
            continue
        points_list.append(orbit_xyz)
        indices = np.arange(offset, offset + orbit_xyz.shape[0], dtype=np.int32)
        lines_list.append(np.concatenate(([orbit_xyz.shape[0]], indices)))
        offset += orbit_xyz.shape[0]
    mesh = pyvista_module.PolyData()
    if not points_list:
        mesh.points = np.zeros((0, 3), dtype=np.float64)
        mesh.lines = np.zeros((0,), dtype=np.int32)
        return mesh
    mesh.points = np.vstack(points_list)
    mesh.lines = np.concatenate(lines_list).astype(np.int32)
    return mesh


def _make_polyline_mesh(pyvista_module: Any, points_xyz: np.ndarray) -> Any:
    points = np.asarray(points_xyz, dtype=np.float64)
    mesh = pyvista_module.PolyData()
    mesh.points = points
    mesh.lines = _polyline_lines(points.shape[0])
    return mesh


def _update_polyline_mesh(mesh: Any, points_xyz: np.ndarray) -> None:
    points = np.asarray(points_xyz, dtype=np.float64)
    current_shape = _mesh_points_shape(mesh)
    lines = None if current_shape == points.shape else _polyline_lines(points.shape[0])
    _set_mesh_geometry(mesh, points, lines=lines)


def _mesh_points_shape(mesh: Any) -> tuple[int, ...] | None:
    points = getattr(mesh, "points", None)
    if points is None:
        return None
    try:
        return tuple(np.asarray(points).shape)
    except Exception:  # noqa: BLE001
        return None


def _segment_points(vectors_xyz: np.ndarray) -> np.ndarray:
    points = np.zeros((vectors_xyz.shape[0] * 2, 3), dtype=np.float64)
    points[1::2] = vectors_xyz
    return points


def _segment_lines(vector_count: int) -> np.ndarray:
    lines = np.empty(vector_count * 3, dtype=np.int32)
    lines[0::3] = 2
    lines[1::3] = np.arange(0, vector_count * 2, 2, dtype=np.int32)
    lines[2::3] = np.arange(1, vector_count * 2, 2, dtype=np.int32)
    return lines


def _polyline_lines(point_count: int) -> np.ndarray:
    return np.concatenate(([point_count], np.arange(point_count, dtype=np.int32)))


def _set_mesh_geometry(
    mesh: Any,
    points_xyz: np.ndarray,
    *,
    lines: np.ndarray | None = None,
) -> None:
    mesh.points = np.asarray(points_xyz, dtype=np.float64)
    if lines is not None:
        mesh.lines = np.asarray(lines, dtype=np.int32)
    _mark_mesh_modified(mesh)


def _mark_mesh_modified(mesh: Any) -> None:
    with suppress(Exception):
        vtk_points = mesh.GetPoints()
        if vtk_points is not None:
            vtk_points.Modified()
    with suppress(Exception):
        mesh.Modified()


def _set_actor_visibility(actor: Any, visible: bool) -> None:
    if actor is None:
        return
    if hasattr(actor, "SetVisibility"):
        actor.SetVisibility(bool(visible))
        return
    if hasattr(actor, "setVisible"):
        actor.setVisible(bool(visible))


def _set_actor_line_width(actor: Any, line_width: float) -> None:
    if actor is None:
        return
    with suppress(Exception):
        prop = actor.GetProperty()
        if prop is not None and hasattr(prop, "SetLineWidth"):
            prop.SetLineWidth(float(line_width))
            return
    if hasattr(actor, "line_width"):
        actor.line_width = float(line_width)


def _active_vector_line_width(emphasize_all_spins: bool) -> float:
    if emphasize_all_spins:
        return THICK_ACTIVE_VECTOR_LINE_WIDTH
    return DEFAULT_ACTIVE_VECTOR_LINE_WIDTH


def _selected_active_vector_line_width(emphasize_all_spins: bool) -> float:
    if emphasize_all_spins:
        return max(ACTIVE_SELECTED_VECTOR_LINE_WIDTH, THICK_ACTIVE_VECTOR_LINE_WIDTH)
    return ACTIVE_SELECTED_VECTOR_LINE_WIDTH


def _compare_vector_line_width(emphasize_all_spins: bool) -> float:
    if emphasize_all_spins:
        return max(COMPARE_VECTOR_LINE_WIDTH, THICK_ACTIVE_VECTOR_LINE_WIDTH)
    return COMPARE_VECTOR_LINE_WIDTH


def _active_orbit_line_width(emphasize_all_spins: bool) -> float:
    return THICK_ACTIVE_ORBIT_LINE_WIDTH if emphasize_all_spins else DEFAULT_ACTIVE_ORBIT_LINE_WIDTH


def _selected_active_orbit_line_width(emphasize_all_spins: bool) -> float:
    if emphasize_all_spins:
        return max(ACTIVE_SELECTED_ORBIT_LINE_WIDTH, THICK_ACTIVE_ORBIT_LINE_WIDTH)
    return ACTIVE_SELECTED_ORBIT_LINE_WIDTH


def _compare_orbit_line_width(emphasize_all_spins: bool) -> float:
    if emphasize_all_spins:
        return max(COMPARE_ORBIT_LINE_WIDTH, THICK_ACTIVE_ORBIT_LINE_WIDTH)
    return COMPARE_ORBIT_LINE_WIDTH


def _comparison_text_lines(
    active_vm: DatasetViewModel,
    active_selection: ResolvedSelection,
    mode: str,
    compare_selection: ResolvedSelection | None,
) -> list[str]:
    active_time_ms = active_vm.get_current_time_s(mode, active_selection.frame_index) * 1.0e3
    lines = [
        f"active slot: {active_selection.slot}",
        f"mode: {mode}",
        f"active acq: {active_selection.acquisition_index}",
        f"active frame: {active_selection.frame_index + 1}/{active_vm.get_frame_count(mode)}",
        f"active time: {active_time_ms:.3f} ms",
        f"active spin: {active_selection.spin_index}",
        f"active delta_f_hz: {active_selection.delta_f_hz:+.3f}",
    ]
    if compare_selection is not None:
        lines.extend(
            [
                f"compare spin: {compare_selection.spin_index}",
                f"compare delta_f_hz: {compare_selection.delta_f_hz:+.3f}",
            ]
        )
    return lines

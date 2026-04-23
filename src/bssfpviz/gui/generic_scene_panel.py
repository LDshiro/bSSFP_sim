"""Generic scene tab for comparison bundles."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from bssfpviz.gui.animation_view_model import AnimationViewModel
from bssfpviz.gui.generic_playback_controller import GenericPlaybackController
from bssfpviz.gui.scene_panel import ScenePanel
from bssfpviz.models.comparison import ComparisonBundle


class GenericScenePanel(QWidget):
    """ScenePanel wrapper with compact generic playback controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._models: dict[str, AnimationViewModel] = {}
        self._controller = GenericPlaybackController(self)
        self._build_ui()
        self._connect_signals()
        self.clear()

    def set_bundle(self, bundle: ComparisonBundle) -> None:
        """Build animation models from a bundle and display Run A."""
        self._models = {
            "run_a": AnimationViewModel.from_simulation_result(bundle.run_a),
            "run_b": AnimationViewModel.from_simulation_result(bundle.run_b),
        }
        self.run_combo.blockSignals(True)
        self.run_combo.clear()
        self.run_combo.addItem(f"Run A: {bundle.run_a.run_label}", "run_a")
        self.run_combo.addItem(f"Run B: {bundle.run_b.run_label}", "run_b")
        self.run_combo.blockSignals(False)
        self._set_active_run("run_a")
        self.note_label.setText("Bundle animation view is read-only.")

    def clear(self) -> None:
        """Clear the scene tab."""
        self._models = {}
        self.run_combo.blockSignals(True)
        self.run_combo.clear()
        self.run_combo.blockSignals(False)
        self._controller.set_view_model(None)
        self.scene_panel.set_generic_controller(self._controller)
        self.scene_panel.show_placeholder("Load a comparison bundle to inspect trajectories.")
        self.frame_slider.setRange(0, 0)
        self.frame_slider.setEnabled(False)
        self.play_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self.forward_button.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.spin_combo.setEnabled(False)
        self.run_combo.setEnabled(False)
        self.frame_label.setText("frame 0/0")
        self.time_label.setText("t = 0.000 ms")
        self.note_label.setText("Load a comparison bundle to enable generic 3D playback.")

    def current_run_key(self) -> str:
        """Return the selected run key."""
        return str(self.run_combo.currentData() or "")

    def frame_count(self) -> int:
        """Return the current active frame count."""
        vm = self._controller.view_model()
        if vm is None:
            return 0
        return int(vm.get_frame_count(self._controller.state().mode))

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.scene_panel = ScenePanel(self)
        layout.addWidget(self.scene_panel, 1)

        controls = QWidget(self)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(6, 6, 6, 6)
        self.run_combo = QComboBox(controls)
        self.run_combo.setObjectName("generic-scene-run-combo")
        self.mode_combo = QComboBox(controls)
        self.mode_combo.setObjectName("generic-scene-mode-combo")
        self.mode_combo.addItem("reference", "reference")
        self.mode_combo.addItem("steady-state", "steady")
        self.spin_combo = QComboBox(controls)
        self.spin_combo.setObjectName("generic-scene-spin-combo")
        self.back_button = QPushButton("<", controls)
        self.play_button = QPushButton("Play", controls)
        self.forward_button = QPushButton(">", controls)
        self.frame_slider = QSlider(Qt.Orientation.Horizontal, controls)
        self.frame_slider.setObjectName("generic-scene-frame-slider")
        self.frame_label = QLabel("frame 0/0", controls)
        self.time_label = QLabel("t = 0.000 ms", controls)
        controls_layout.addWidget(self.run_combo)
        controls_layout.addWidget(self.mode_combo)
        controls_layout.addWidget(self.spin_combo)
        controls_layout.addWidget(self.back_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.forward_button)
        controls_layout.addWidget(self.frame_slider, 1)
        controls_layout.addWidget(self.frame_label)
        controls_layout.addWidget(self.time_label)
        layout.addWidget(controls)

        self.note_label = QLabel("", self)
        self.note_label.setObjectName("generic-scene-note")
        self.note_label.setWordWrap(True)
        layout.addWidget(self.note_label)

    def _connect_signals(self) -> None:
        self.scene_panel.set_generic_controller(self._controller)
        self.run_combo.currentIndexChanged.connect(self._on_run_changed)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.spin_combo.currentIndexChanged.connect(self._on_spin_changed)
        self.back_button.clicked.connect(self._controller.step_backward)
        self.play_button.clicked.connect(self._controller.toggle_play)
        self.forward_button.clicked.connect(self._controller.step_forward)
        self.frame_slider.valueChanged.connect(self._on_slider_changed)
        self._controller.state_changed.connect(self._sync_from_controller)
        self._controller.frame_changed.connect(self._sync_from_controller)

    def _set_active_run(self, run_key: str) -> None:
        model = self._models.get(run_key)
        self._controller.set_view_model(model)
        self.scene_panel.set_generic_controller(self._controller)
        enabled = model is not None
        for widget in [
            self.frame_slider,
            self.play_button,
            self.back_button,
            self.forward_button,
            self.mode_combo,
            self.spin_combo,
            self.run_combo,
        ]:
            widget.setEnabled(enabled)
        self._rebuild_spin_combo(model)
        self._sync_from_controller()

    def _rebuild_spin_combo(self, model: AnimationViewModel | None) -> None:
        self.spin_combo.blockSignals(True)
        self.spin_combo.clear()
        if model is not None:
            for index in range(model.n_spins):
                value = model.get_selected_delta_f_hz(index)
                self.spin_combo.addItem(f"{model.selector_label} {index} ({value:+.3f})", index)
        self.spin_combo.blockSignals(False)

    def _sync_from_controller(self, *_args: object) -> None:
        model = self._controller.view_model()
        state = self._controller.state()
        if model is None:
            return
        frame_count = model.get_frame_count(state.mode)
        self.frame_slider.blockSignals(True)
        self.frame_slider.setRange(0, max(0, frame_count - 1))
        self.frame_slider.setValue(state.frame_index)
        self.frame_slider.blockSignals(False)
        self.play_button.setText("Pause" if state.is_playing else "Play")
        self.frame_label.setText(f"frame {state.frame_index + 1}/{frame_count}")
        time_ms = model.get_current_time_s(state.mode, state.frame_index) * 1.0e3
        self.time_label.setText(f"t = {time_ms:.3f} ms")

    def _on_run_changed(self, _index: int) -> None:
        self._set_active_run(self.current_run_key())

    def _on_mode_changed(self, _index: int) -> None:
        self._controller.set_mode(str(self.mode_combo.currentData()))

    def _on_spin_changed(self, index: int) -> None:
        if index >= 0:
            self._controller.set_spin_index(index)

    def _on_slider_changed(self, index: int) -> None:
        self._controller.set_frame_index(index)

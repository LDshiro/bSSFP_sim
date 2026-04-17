"""Playback controls synchronized with the Chapter 6 controller."""

from __future__ import annotations

from contextlib import suppress

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

from bssfpviz.gui.comparison_controller import ComparisonController
from bssfpviz.gui.dataset_view_model import DatasetViewModel
from bssfpviz.gui.playback_controller import PlaybackController, PlaybackState


class PlaybackBar(QWidget):
    """Thin UI wrapper around :class:`PlaybackController`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller: PlaybackController | ComparisonController | None = None
        self._build_ui()
        self._connect_local_signals()
        self.set_enabled_for_dataset(False)
        self.set_frame_range(0)

    def set_controller(
        self,
        controller: PlaybackController | ComparisonController | None,
    ) -> None:
        """Attach a playback controller and mirror its state."""
        if self._controller is controller:
            if controller is not None:
                self._on_state_changed(controller.state())
            return

        if self._controller is not None:
            with suppress(TypeError):
                self._controller.state_changed.disconnect(self._handle_controller_state_changed)
            with suppress(TypeError):
                self._controller.frame_changed.disconnect(self._handle_frame_changed)

        self._controller = controller
        if controller is None:
            self._rebuild_dataset_widgets(None)
            self.set_enabled_for_dataset(False)
            self._update_text(0, 0.0)
            self._update_context_labels()
            return

        controller.state_changed.connect(self._handle_controller_state_changed)
        controller.frame_changed.connect(self._handle_frame_changed)
        self._on_state_changed(controller.state())

    def set_frame_range(self, n_frames: int) -> None:
        """Set the slider range explicitly for compatibility with older callers."""
        maximum = max(0, int(n_frames) - 1)
        self.frame_slider.blockSignals(True)
        self.frame_slider.setRange(0, maximum)
        self.frame_slider.blockSignals(False)
        self._update_text(self.frame_slider.value(), 0.0)

    def set_current_frame(self, index: int) -> None:
        """Update the current frame widget state."""
        maximum = self.frame_slider.maximum()
        clamped = max(0, min(int(index), maximum))
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(clamped)
        self.frame_slider.blockSignals(False)
        time_s = 0.0
        vm = self._controller.view_model() if self._controller is not None else None
        if self._controller is not None and vm is not None:
            state = self._controller.state()
            time_s = vm.get_current_time_s(state.mode, clamped)
        self._update_text(clamped, time_s)

    def set_enabled_for_dataset(self, enabled: bool) -> None:
        """Enable or disable the interactive controls."""
        widgets = [
            self.mode_combo,
            self.acq_combo,
            self.spin_combo,
            self.first_button,
            self.back_button,
            self.play_pause_button,
            self.forward_button,
            self.last_button,
            self.loop_checkbox,
            self.fps_spinbox,
            self.frame_slider,
        ]
        for widget in widgets:
            widget.setEnabled(enabled)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.mode_combo = QComboBox(self)
        self.mode_combo.setObjectName("playback-mode-combo")
        self.mode_combo.addItem("reference", "reference")
        self.mode_combo.addItem("steady-state", "steady")

        self.acq_combo = QComboBox(self)
        self.acq_combo.setObjectName("playback-acq-combo")

        self.spin_combo = QComboBox(self)
        self.spin_combo.setObjectName("playback-spin-combo")

        self.first_button = QPushButton("|<", self)
        self.first_button.setObjectName("playback-first-button")
        self.back_button = QPushButton("<", self)
        self.back_button.setObjectName("playback-back-button")
        self.play_pause_button = QPushButton("Play", self)
        self.play_pause_button.setObjectName("playback-play-button")
        self.forward_button = QPushButton(">", self)
        self.forward_button.setObjectName("playback-forward-button")
        self.last_button = QPushButton(">|", self)
        self.last_button.setObjectName("playback-last-button")

        self.loop_checkbox = QCheckBox("Loop", self)
        self.loop_checkbox.setObjectName("playback-loop-checkbox")
        self.loop_checkbox.setChecked(True)

        self.fps_spinbox = QDoubleSpinBox(self)
        self.fps_spinbox.setObjectName("playback-fps-spinbox")
        self.fps_spinbox.setRange(0.25, 120.0)
        self.fps_spinbox.setDecimals(2)
        self.fps_spinbox.setSingleStep(0.25)
        self.fps_spinbox.setValue(30.0)
        self.fps_spinbox.setSuffix(" fps")

        self.frame_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.frame_slider.setObjectName("playback-slider")

        self.frame_label = QLabel("frame 0/0", self)
        self.frame_label.setObjectName("playback-frame-label")
        self.time_label = QLabel("t = 0.000 ms", self)
        self.time_label.setObjectName("playback-time-label")
        self.active_slot_label = QLabel("active: primary", self)
        self.active_slot_label.setObjectName("playback-active-slot-label")
        self.compare_info_label = QLabel("compare: disabled", self)
        self.compare_info_label.setObjectName("playback-compare-info-label")

        layout.addWidget(self.mode_combo)
        layout.addWidget(self.acq_combo)
        layout.addWidget(self.spin_combo)
        layout.addWidget(self.active_slot_label)
        layout.addWidget(self.compare_info_label)
        layout.addWidget(self.first_button)
        layout.addWidget(self.back_button)
        layout.addWidget(self.play_pause_button)
        layout.addWidget(self.forward_button)
        layout.addWidget(self.last_button)
        layout.addWidget(self.loop_checkbox)
        layout.addWidget(self.fps_spinbox)
        layout.addWidget(self.frame_slider, 1)
        layout.addWidget(self.frame_label)
        layout.addWidget(self.time_label)

    def _connect_local_signals(self) -> None:
        self.mode_combo.currentIndexChanged.connect(self._on_mode_combo_changed)
        self.acq_combo.currentIndexChanged.connect(self._on_acq_combo_changed)
        self.spin_combo.currentIndexChanged.connect(self._on_spin_combo_changed)
        self.first_button.clicked.connect(self._on_first_clicked)
        self.back_button.clicked.connect(self._on_back_clicked)
        self.play_pause_button.clicked.connect(self._on_play_pause_clicked)
        self.forward_button.clicked.connect(self._on_forward_clicked)
        self.last_button.clicked.connect(self._on_last_clicked)
        self.loop_checkbox.toggled.connect(self._on_loop_toggled)
        self.fps_spinbox.valueChanged.connect(self._on_fps_changed)
        self.frame_slider.valueChanged.connect(self._on_slider_changed)

    def _on_state_changed(self, state: PlaybackState) -> None:
        vm = self._controller.view_model() if self._controller is not None else None
        self._rebuild_dataset_widgets(vm)
        enabled = vm is not None
        self.set_enabled_for_dataset(enabled)
        if not enabled:
            self.play_pause_button.setText("Play")
            self._update_text(0, 0.0)
            self._update_context_labels()
            return
        assert vm is not None

        self._set_mode_combo_value(state.mode)
        self._set_combo_index(self.acq_combo, state.acquisition_index)
        self._set_combo_index(self.spin_combo, state.spin_index)

        self.loop_checkbox.blockSignals(True)
        self.loop_checkbox.setChecked(state.loop)
        self.loop_checkbox.blockSignals(False)

        self.fps_spinbox.blockSignals(True)
        self.fps_spinbox.setValue(state.fps)
        self.fps_spinbox.blockSignals(False)

        frame_count = vm.get_frame_count(state.mode)
        self.set_frame_range(frame_count)
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(state.frame_index)
        self.frame_slider.blockSignals(False)
        self.play_pause_button.setText("Pause" if state.is_playing else "Play")
        current_time_s = vm.get_current_time_s(state.mode, state.frame_index)
        self._update_text(
            state.frame_index,
            current_time_s,
        )
        self._update_context_labels()

    def _handle_controller_state_changed(self, *_args: object) -> None:
        if self._controller is not None:
            self._on_state_changed(self._controller.state())

    def _handle_frame_changed(self, _index: int) -> None:
        if self._controller is None:
            return
        vm = self._controller.view_model()
        if vm is None:
            self._update_text(0, 0.0)
            return
        state = self._controller.state()
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(state.frame_index)
        self.frame_slider.blockSignals(False)
        self._update_text(state.frame_index, vm.get_current_time_s(state.mode, state.frame_index))

    def _rebuild_dataset_widgets(self, vm: DatasetViewModel | None) -> None:
        if vm is None:
            self.acq_combo.clear()
            self.spin_combo.clear()
            return

        acq_count = vm.n_acq
        spin_count = vm.n_spins

        if self.acq_combo.count() != acq_count:
            self.acq_combo.blockSignals(True)
            self.acq_combo.clear()
            for acquisition_index in range(acq_count):
                self.acq_combo.addItem(f"acq {acquisition_index}", acquisition_index)
            self.acq_combo.blockSignals(False)

        if self.spin_combo.count() != spin_count:
            self.spin_combo.blockSignals(True)
            self.spin_combo.clear()
            for spin_index in range(spin_count):
                delta_f_hz = vm.get_selected_delta_f_hz(spin_index)
                self.spin_combo.addItem(
                    f"spin {spin_index} ({delta_f_hz:+.3f} Hz)",
                    spin_index,
                )
            self.spin_combo.blockSignals(False)

    def _set_mode_combo_value(self, mode: str) -> None:
        index = self.mode_combo.findData(mode)
        if index < 0:
            return
        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentIndex(index)
        self.mode_combo.blockSignals(False)

    def _set_combo_index(self, combo: QComboBox, index: int) -> None:
        if combo.count() == 0:
            return
        clamped = max(0, min(index, combo.count() - 1))
        combo.blockSignals(True)
        combo.setCurrentIndex(clamped)
        combo.blockSignals(False)

    def _update_text(self, frame_index: int, time_s: float) -> None:
        total = max(0, self.frame_slider.maximum() + 1)
        if total == 0:
            self.frame_label.setText("frame 0/0")
            self.time_label.setText("t = 0.000 ms")
            return
        self.frame_label.setText(f"frame {frame_index + 1}/{total}")
        self.time_label.setText(f"t = {time_s * 1.0e3:.3f} ms")

    def _update_context_labels(self) -> None:
        if self._controller is None:
            self.active_slot_label.setText("active: -")
            self.compare_info_label.setText("compare: disabled")
            return
        if isinstance(self._controller, ComparisonController):
            session = self._controller.session_state()
            self.active_slot_label.setText(f"active: {session.active_slot}")
            other_selection = self._controller.resolve_other_selection()
            if session.compare_enabled and other_selection is not None:
                self.compare_info_label.setText(
                    f"mapped {other_selection.slot}: spin {other_selection.spin_index} "
                    f"({other_selection.delta_f_hz:+.3f} Hz)"
                )
            else:
                self.compare_info_label.setText("compare: disabled")
            return
        self.active_slot_label.setText("active: primary")
        self.compare_info_label.setText("compare: disabled")

    def _on_mode_combo_changed(self, index: int) -> None:
        if self._controller is None or index < 0:
            return
        user_data = self.mode_combo.itemData(index)
        if isinstance(user_data, str):
            self._controller.set_mode(user_data)

    def _on_acq_combo_changed(self, index: int) -> None:
        if self._controller is not None and index >= 0:
            self._controller.set_acquisition_index(index)

    def _on_spin_combo_changed(self, index: int) -> None:
        if self._controller is not None and index >= 0:
            self._controller.set_spin_index(index)

    def _on_first_clicked(self) -> None:
        if self._controller is not None:
            self._controller.jump_first()

    def _on_back_clicked(self) -> None:
        if self._controller is not None:
            self._controller.step_backward()

    def _on_play_pause_clicked(self) -> None:
        if self._controller is not None:
            self._controller.toggle_play()

    def _on_forward_clicked(self) -> None:
        if self._controller is not None:
            self._controller.step_forward()

    def _on_last_clicked(self) -> None:
        if self._controller is not None:
            self._controller.jump_last()

    def _on_loop_toggled(self, checked: bool) -> None:
        if self._controller is not None:
            self._controller.set_loop(checked)

    def _on_fps_changed(self, value: float) -> None:
        if self._controller is not None:
            self._controller.set_fps(value)

    def _on_slider_changed(self, value: int) -> None:
        if self._controller is not None:
            self._controller.set_frame_index(value)

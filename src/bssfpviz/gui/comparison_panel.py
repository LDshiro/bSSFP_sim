"""Comparison-control widget for Chapter 7."""

from __future__ import annotations

from contextlib import suppress

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from bssfpviz.gui.comparison_controller import ComparisonController


class ComparisonPanel(QWidget):
    """Expose active/compare controls and loaded dataset paths."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller: ComparisonController | None = None
        self._build_ui()

    def set_controller(self, controller: ComparisonController | None) -> None:
        """Attach one comparison controller."""
        if self._controller is controller:
            self.refresh()
            return

        if self._controller is not None:
            with suppress(TypeError):
                self._controller.datasets_changed.disconnect(self.refresh)
            with suppress(TypeError):
                self._controller.selection_changed.disconnect(self.refresh)

        self._controller = controller
        if controller is not None:
            controller.datasets_changed.connect(self.refresh)
            controller.selection_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        """Refresh controls from the controller state."""
        if self._controller is None:
            self.primary_path_label.setText("-")
            self.compare_path_label.setText("-")
            return

        session = self._controller.session_state()
        self._set_combo_value(self.active_slot_combo, session.active_slot)
        self.compare_enabled_checkbox.blockSignals(True)
        self.compare_enabled_checkbox.setChecked(session.compare_enabled)
        self.compare_enabled_checkbox.blockSignals(False)
        self.compare_visible_checkbox.blockSignals(True)
        self.compare_visible_checkbox.setChecked(session.compare_visible_in_scene)
        self.compare_visible_checkbox.blockSignals(False)
        self.thick_all_spins_checkbox.blockSignals(True)
        self.thick_all_spins_checkbox.setChecked(session.thick_all_spins_in_scene)
        self.thick_all_spins_checkbox.blockSignals(False)
        self.primary_path_label.setText(session.primary_path or "-")
        self.compare_path_label.setText(session.compare_path or "-")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.active_slot_combo = QComboBox(self)
        self.active_slot_combo.setObjectName("compare-active-slot-combo")
        self.active_slot_combo.addItem("primary", "primary")
        self.active_slot_combo.addItem("compare", "compare")

        self.compare_enabled_checkbox = QCheckBox(self)
        self.compare_enabled_checkbox.setObjectName("compare-enabled-checkbox")
        self.compare_visible_checkbox = QCheckBox(self)
        self.compare_visible_checkbox.setObjectName("compare-visible-checkbox")
        self.thick_all_spins_checkbox = QCheckBox(self)
        self.thick_all_spins_checkbox.setObjectName("scene-thick-all-spins-checkbox")

        self.primary_path_label = QLabel("-", self)
        self.primary_path_label.setObjectName("primary-path-label")
        self.primary_path_label.setWordWrap(True)
        self.compare_path_label = QLabel("-", self)
        self.compare_path_label.setObjectName("compare-path-label")
        self.compare_path_label.setWordWrap(True)

        form.addRow("active slot", self.active_slot_combo)
        form.addRow("compare enabled", self.compare_enabled_checkbox)
        form.addRow("compare visible", self.compare_visible_checkbox)
        form.addRow("thick all spins", self.thick_all_spins_checkbox)
        form.addRow("primary path", self.primary_path_label)
        form.addRow("compare path", self.compare_path_label)

        layout.addLayout(form)
        layout.addStretch(1)

        self.active_slot_combo.currentIndexChanged.connect(self._on_active_slot_changed)
        self.compare_enabled_checkbox.toggled.connect(self._on_compare_enabled_changed)
        self.compare_visible_checkbox.toggled.connect(self._on_compare_visible_changed)
        self.thick_all_spins_checkbox.toggled.connect(self._on_thick_all_spins_changed)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index < 0:
            return
        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def _on_active_slot_changed(self, index: int) -> None:
        if self._controller is None or index < 0:
            return
        data = self.active_slot_combo.itemData(index)
        if isinstance(data, str):
            self._controller.set_active_slot(data)

    def _on_compare_enabled_changed(self, checked: bool) -> None:
        if self._controller is not None:
            self._controller.set_compare_enabled(checked)

    def _on_compare_visible_changed(self, checked: bool) -> None:
        if self._controller is not None:
            self._controller.set_compare_visible_in_scene(checked)

    def _on_thick_all_spins_changed(self, checked: bool) -> None:
        if self._controller is not None:
            self._controller.set_thick_all_spins_in_scene(checked)

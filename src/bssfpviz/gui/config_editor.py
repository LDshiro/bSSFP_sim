"""Configuration editor widget for the Chapter 5 GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bssfpviz.gui.adapters import (
    load_run_config_from_yaml,
    make_default_run_config,
    save_run_config_to_yaml,
)
from bssfpviz.models.run_config import (
    IntegrationConfig,
    MetaConfig,
    OutputConfig,
    PhaseCycleConfig,
    PhysicsConfig,
    RunConfig,
    SequenceConfig,
    SweepConfig,
)


class ConfigEditor(QWidget):
    """Scrollable form that edits a Chapter 4/5 run configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.set_config(make_default_run_config())

    def set_config(self, config: Any) -> None:
        """Populate the editor from a config object."""
        run_config = config if isinstance(config, RunConfig) else make_default_run_config()
        self.case_name_edit.setText(run_config.meta.case_name)
        self.description_edit.setPlainText(run_config.meta.description)

        self.t1_spin.setValue(run_config.physics.t1_s)
        self.t2_spin.setValue(run_config.physics.t2_s)
        self.m0_spin.setValue(run_config.physics.m0)

        self.tr_spin.setValue(run_config.sequence.tr_s)
        self.rf_duration_spin.setValue(run_config.sequence.rf_duration_s)
        self.n_rf_spin.setValue(run_config.sequence.n_rf)
        self.alpha_deg_spin.setValue(run_config.sequence.alpha_deg)
        self.waveform_kind_combo.setCurrentText(run_config.sequence.waveform_kind)
        self.readout_fraction_spin.setValue(run_config.sequence.readout_fraction_of_free)

        self._set_phase_cycles(run_config.phase_cycles.values_deg.tolist())

        self.delta_f_start_spin.setValue(run_config.sweep.start_hz)
        self.delta_f_stop_spin.setValue(run_config.sweep.stop_hz)
        self.delta_f_count_spin.setValue(run_config.sweep.count)

        self.rk_method_combo.setCurrentText(run_config.integration.rk_method)
        self.rk_rtol_spin.setValue(run_config.integration.rk_rtol)
        self.rk_atol_spin.setValue(run_config.integration.rk_atol)
        self.rk_max_step_spin.setValue(run_config.integration.rk_max_step_s)
        self.rk_superperiods_spin.setValue(run_config.integration.rk_superperiods)
        self.save_every_step_check.setChecked(run_config.integration.save_every_time_step)

        self.save_profiles_check.setChecked(run_config.output.save_profiles)
        self.save_rk_check.setChecked(run_config.output.save_rk_trajectories)
        self.save_orbit_check.setChecked(run_config.output.save_steady_state_orbit)
        self.save_fixed_points_check.setChecked(run_config.output.save_fixed_points)

    def get_config(self) -> Any:
        """Read the current widget values into a RunConfig."""
        tr_s = self.tr_spin.value()
        rf_duration_s = self.rf_duration_spin.value()
        if rf_duration_s >= tr_s:
            msg = "rf_duration_s must be smaller than TR_s."
            raise ValueError(msg)

        phase_rows = self._phase_cycles_from_table()
        if len(phase_rows) == 0:
            msg = "At least one acquisition row is required."
            raise ValueError(msg)

        return RunConfig(
            meta=MetaConfig(
                case_name=self.case_name_edit.text().strip(),
                description=self.description_edit.toPlainText().strip(),
            ),
            physics=PhysicsConfig(
                t1_s=self.t1_spin.value(),
                t2_s=self.t2_spin.value(),
                m0=self.m0_spin.value(),
            ),
            sequence=SequenceConfig(
                tr_s=tr_s,
                rf_duration_s=rf_duration_s,
                n_rf=self.n_rf_spin.value(),
                alpha_deg=self.alpha_deg_spin.value(),
                waveform_kind=self.waveform_kind_combo.currentText(),
                readout_fraction_of_free=self.readout_fraction_spin.value(),
            ),
            phase_cycles=PhaseCycleConfig(values_deg=np.asarray(phase_rows, dtype=np.float64)),
            sweep=SweepConfig(
                start_hz=self.delta_f_start_spin.value(),
                stop_hz=self.delta_f_stop_spin.value(),
                count=self.delta_f_count_spin.value(),
            ),
            integration=IntegrationConfig(
                rk_method=self.rk_method_combo.currentText(),
                rk_rtol=self.rk_rtol_spin.value(),
                rk_atol=self.rk_atol_spin.value(),
                rk_max_step_s=self.rk_max_step_spin.value(),
                rk_superperiods=self.rk_superperiods_spin.value(),
                save_every_time_step=self.save_every_step_check.isChecked(),
            ),
            output=OutputConfig(
                save_profiles=self.save_profiles_check.isChecked(),
                save_rk_trajectories=self.save_rk_check.isChecked(),
                save_steady_state_orbit=self.save_orbit_check.isChecked(),
                save_fixed_points=self.save_fixed_points_check.isChecked(),
            ),
        )

    def load_yaml(self, path: Path) -> Any:
        """Load a YAML config into the editor and return it."""
        config = load_run_config_from_yaml(path)
        self.set_config(config)
        return config

    def save_yaml(self, path: Path) -> None:
        """Save the current config to YAML."""
        save_run_config_to_yaml(self.get_config(), path)

    def add_acquisition_row(self) -> None:
        """Append one phase-cycle row to the acquisition table."""
        row_index = self.phase_cycle_table.rowCount()
        self.phase_cycle_table.insertRow(row_index)
        self.phase_cycle_table.setItem(row_index, 0, QTableWidgetItem("0.0"))
        self.phase_cycle_table.setItem(row_index, 1, QTableWidgetItem("0.0"))

    def remove_acquisition_row(self) -> None:
        """Remove the last acquisition row while keeping at least one row."""
        row_count = self.phase_cycle_table.rowCount()
        if row_count > 1:
            self.phase_cycle_table.removeRow(row_count - 1)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        root_layout.addWidget(scroll_area, 1)

        content_widget = QWidget(scroll_area)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(content_widget)

        self.case_name_edit = QLineEdit(content_widget)
        self.description_edit = QPlainTextEdit(content_widget)
        self.description_edit.setMaximumHeight(90)
        content_layout.addWidget(self._build_meta_group(content_widget))

        self.t1_spin = self._make_double_spin(1.0e-6, 1000.0, 6, 0.001, content_widget)
        self.t2_spin = self._make_double_spin(1.0e-6, 1000.0, 6, 0.001, content_widget)
        self.m0_spin = self._make_double_spin(1.0e-6, 1000.0, 6, 0.1, content_widget)
        content_layout.addWidget(self._build_physics_group(content_widget))

        self.tr_spin = self._make_double_spin(1.0e-6, 10.0, 6, 0.0001, content_widget)
        self.rf_duration_spin = self._make_double_spin(1.0e-6, 10.0, 6, 0.0001, content_widget)
        self.n_rf_spin = self._make_int_spin(1, 10000, content_widget)
        self.alpha_deg_spin = self._make_double_spin(0.001, 3600.0, 3, 1.0, content_widget)
        self.waveform_kind_combo = QComboBox(content_widget)
        self.waveform_kind_combo.addItems(["hann", "rect"])
        self.readout_fraction_spin = self._make_double_spin(0.0, 1.0, 3, 0.1, content_widget)
        content_layout.addWidget(self._build_sequence_group(content_widget))

        self.phase_cycle_table = QTableWidget(0, 2, content_widget)
        self.phase_cycle_table.setObjectName("phase-cycle-table")
        self.phase_cycle_table.setHorizontalHeaderLabels(["pulse0_deg", "pulse1_deg"])
        self.phase_cycle_table.horizontalHeader().setStretchLastSection(True)
        self.phase_cycle_table.verticalHeader().setVisible(False)
        self.add_acquisition_button = QPushButton("Add Acquisition", content_widget)
        self.add_acquisition_button.clicked.connect(self.add_acquisition_row)
        self.remove_acquisition_button = QPushButton("Remove Acquisition", content_widget)
        self.remove_acquisition_button.clicked.connect(self.remove_acquisition_row)
        content_layout.addWidget(self._build_phase_cycle_group(content_widget))

        self.delta_f_start_spin = self._make_double_spin(-1.0e6, 1.0e6, 3, 1.0, content_widget)
        self.delta_f_stop_spin = self._make_double_spin(-1.0e6, 1.0e6, 3, 1.0, content_widget)
        self.delta_f_count_spin = self._make_int_spin(1, 100000, content_widget)
        content_layout.addWidget(self._build_sweep_group(content_widget))

        self.rk_method_combo = QComboBox(content_widget)
        self.rk_method_combo.addItems(["RK45"])
        self.rk_rtol_spin = self._make_double_spin(1.0e-12, 1.0, 12, 1.0e-7, content_widget)
        self.rk_atol_spin = self._make_double_spin(1.0e-12, 1.0, 12, 1.0e-9, content_widget)
        self.rk_max_step_spin = self._make_double_spin(1.0e-7, 1.0, 7, 1.0e-5, content_widget)
        self.rk_superperiods_spin = self._make_int_spin(1, 100000, content_widget)
        self.save_every_step_check = QCheckBox(content_widget)
        content_layout.addWidget(self._build_integration_group(content_widget))

        self.save_profiles_check = QCheckBox(content_widget)
        self.save_rk_check = QCheckBox(content_widget)
        self.save_orbit_check = QCheckBox(content_widget)
        self.save_fixed_points_check = QCheckBox(content_widget)
        content_layout.addWidget(self._build_output_group(content_widget))
        content_layout.addStretch(1)

        self.run_button = QPushButton("Run Compute", self)
        self.run_button.setObjectName("run-compute-button")
        root_layout.addWidget(self.run_button)

    def _build_meta_group(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Meta", parent)
        layout = QFormLayout(group)
        layout.addRow("case_name", self.case_name_edit)
        layout.addRow("description", self.description_edit)
        return group

    def _build_physics_group(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Physics", parent)
        layout = QFormLayout(group)
        layout.addRow("T1_s", self.t1_spin)
        layout.addRow("T2_s", self.t2_spin)
        layout.addRow("M0", self.m0_spin)
        return group

    def _build_sequence_group(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Sequence", parent)
        layout = QFormLayout(group)
        layout.addRow("TR_s", self.tr_spin)
        layout.addRow("rf_duration_s", self.rf_duration_spin)
        layout.addRow("n_rf", self.n_rf_spin)
        layout.addRow("alpha_deg", self.alpha_deg_spin)
        layout.addRow("waveform_kind", self.waveform_kind_combo)
        layout.addRow("readout_fraction_of_free", self.readout_fraction_spin)
        return group

    def _build_phase_cycle_group(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Phase cycles", parent)
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel("Acquisition rows with 2 pulse phases [deg]", group))
        layout.addWidget(self.phase_cycle_table)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_acquisition_button)
        button_layout.addWidget(self.remove_acquisition_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)
        return group

    def _build_sweep_group(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Sweep", parent)
        layout = QFormLayout(group)
        layout.addRow("delta_f_start_hz", self.delta_f_start_spin)
        layout.addRow("delta_f_stop_hz", self.delta_f_stop_spin)
        layout.addRow("delta_f_count", self.delta_f_count_spin)
        return group

    def _build_integration_group(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Integration", parent)
        layout = QFormLayout(group)
        layout.addRow("rk_method", self.rk_method_combo)
        layout.addRow("rk_rtol", self.rk_rtol_spin)
        layout.addRow("rk_atol", self.rk_atol_spin)
        layout.addRow("rk_max_step_s", self.rk_max_step_spin)
        layout.addRow("rk_superperiods", self.rk_superperiods_spin)
        layout.addRow("save_every_time_step", self.save_every_step_check)
        return group

    def _build_output_group(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Output", parent)
        layout = QFormLayout(group)
        layout.addRow("save_profiles", self.save_profiles_check)
        layout.addRow("save_rk_trajectories", self.save_rk_check)
        layout.addRow("save_steady_state_orbit", self.save_orbit_check)
        layout.addRow("save_fixed_points", self.save_fixed_points_check)
        return group

    def _set_phase_cycles(self, values: list[list[float]]) -> None:
        self.phase_cycle_table.setRowCount(0)
        for row in values:
            row_index = self.phase_cycle_table.rowCount()
            self.phase_cycle_table.insertRow(row_index)
            self.phase_cycle_table.setItem(row_index, 0, QTableWidgetItem(f"{float(row[0]):.6f}"))
            self.phase_cycle_table.setItem(row_index, 1, QTableWidgetItem(f"{float(row[1]):.6f}"))

    def _phase_cycles_from_table(self) -> list[list[float]]:
        rows: list[list[float]] = []
        for row_index in range(self.phase_cycle_table.rowCount()):
            row_values: list[float] = []
            for column_index in range(self.phase_cycle_table.columnCount()):
                item = self.phase_cycle_table.item(row_index, column_index)
                text = item.text().strip() if item is not None else "0.0"
                row_values.append(float(text or "0.0"))
            rows.append(row_values)
        return rows

    @staticmethod
    def _make_double_spin(
        minimum: float,
        maximum: float,
        decimals: int,
        single_step: float,
        parent: QWidget,
    ) -> QDoubleSpinBox:
        widget = QDoubleSpinBox(parent)
        widget.setRange(minimum, maximum)
        widget.setDecimals(decimals)
        widget.setSingleStep(single_step)
        widget.setKeyboardTracking(False)
        return widget

    @staticmethod
    def _make_int_spin(minimum: int, maximum: int, parent: QWidget) -> QSpinBox:
        widget = QSpinBox(parent)
        widget.setRange(minimum, maximum)
        return widget

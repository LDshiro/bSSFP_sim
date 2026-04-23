"""Structured editor for generic comparison experiment configs."""

from __future__ import annotations

from pathlib import Path

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
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bssfpviz.models.comparison import (
    BSSFPFamilyConfig,
    CommonPhysicsConfig,
    ExperimentConfig,
    ExperimentOutputConfig,
    ExperimentRunConfig,
    FastSEFamilyConfig,
    SequenceFamily,
    VFAFSEFamilyConfig,
)
from bssfpviz.models.run_config import (
    IntegrationConfig,
    OutputConfig,
    PhaseCycleConfig,
    SequenceConfig,
    SweepConfig,
)


class ExperimentEditor(QWidget):
    """Family-aware form that edits an :class:`ExperimentConfig`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.set_config(make_default_experiment_config())

    def set_config(self, config: ExperimentConfig) -> None:
        """Populate this editor from a generic experiment config."""
        self.comparison_scope_combo.setCurrentText(config.comparison_scope)
        self.matched_te_check.setChecked("matched_TE_contrast" in config.comparison_modes)
        self.matched_resolution_check.setChecked("matched_resolution" in config.comparison_modes)
        self.matched_voxel_check.setChecked("matched_voxel" in config.comparison_modes)
        self.t1_spin.setValue(config.common_physics.t1_s)
        self.t2_spin.setValue(config.common_physics.t2_s)
        self.m0_spin.setValue(config.common_physics.m0)
        self.run_a_editor.set_run_config(config.run_a)
        self.run_b_editor.set_run_config(config.run_b)
        self.summary_json_edit.setText(config.output.summary_json or "")

    def get_config(self) -> ExperimentConfig:
        """Read widget state into a validated :class:`ExperimentConfig`."""
        modes: list[str] = []
        if self.matched_te_check.isChecked():
            modes.append("matched_TE_contrast")
        if self.matched_resolution_check.isChecked():
            modes.append("matched_resolution")
        if self.matched_voxel_check.isChecked():
            modes.append("matched_voxel")
        if not modes:
            msg = "At least one comparison mode must be selected."
            raise ValueError(msg)
        return ExperimentConfig(
            comparison_scope=self.comparison_scope_combo.currentText(),
            common_physics=CommonPhysicsConfig(
                t1_s=self.t1_spin.value(),
                t2_s=self.t2_spin.value(),
                m0=self.m0_spin.value(),
            ),
            run_a=self.run_a_editor.get_run_config(default_label="run_a"),
            run_b=self.run_b_editor.get_run_config(default_label="run_b"),
            comparison_modes=tuple(modes),
            output=ExperimentOutputConfig(
                summary_json=self.summary_json_edit.text().strip() or None
            ),
        )

    def load_yaml(self, path: Path) -> ExperimentConfig:
        """Load one YAML file into the editor and return the parsed config."""
        config = ExperimentConfig.from_yaml(path)
        self.set_config(config)
        return config

    def save_yaml(self, path: Path) -> ExperimentConfig:
        """Save the current editor config to YAML and return it."""
        config = self.get_config()
        config.to_yaml(path)
        return config

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        root_layout.addWidget(scroll, 1)

        content = QWidget(scroll)
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(content)

        tabs = QTabWidget(content)
        tabs.setObjectName("experiment-editor-tabs")
        tabs.addTab(self._build_common_tab(tabs), "Common")
        self.run_a_editor = _RunBranchEditor("Run A", tabs)
        tabs.addTab(self.run_a_editor, "Run A")
        self.run_b_editor = _RunBranchEditor("Run B", tabs)
        tabs.addTab(self.run_b_editor, "Run B")
        tabs.addTab(self._build_output_tab(tabs), "Output")
        content_layout.addWidget(tabs)

    def _build_common_tab(self, parent: QWidget) -> QWidget:
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        comparison_group = QGroupBox("Comparison", widget)
        comparison_layout = QFormLayout(comparison_group)
        self.comparison_scope_combo = QComboBox(comparison_group)
        self.comparison_scope_combo.setObjectName("experiment-comparison-scope")
        self.comparison_scope_combo.addItems(["physics_only", "protocol_realistic"])
        protocol_note = QLabel(
            "protocol_realistic, scan-time, and SAR controls are reserved for a later phase.",
            comparison_group,
        )
        protocol_note.setWordWrap(True)
        self.matched_te_check = QCheckBox("matched_TE_contrast", comparison_group)
        self.matched_resolution_check = QCheckBox("matched_resolution", comparison_group)
        self.matched_voxel_check = QCheckBox("matched_voxel", comparison_group)
        comparison_layout.addRow("comparison_scope", self.comparison_scope_combo)
        comparison_layout.addRow(self.matched_te_check)
        comparison_layout.addRow(self.matched_resolution_check)
        comparison_layout.addRow(self.matched_voxel_check)
        comparison_layout.addRow("note", protocol_note)
        layout.addWidget(comparison_group)

        physics_group = QGroupBox("Common Physics", widget)
        physics_layout = QFormLayout(physics_group)
        self.t1_spin = _double_spin(1.0e-9, 1.0e12, 6, 0.01, physics_group)
        self.t2_spin = _double_spin(1.0e-9, 1.0e12, 6, 0.01, physics_group)
        self.m0_spin = _double_spin(1.0e-9, 1.0e6, 6, 0.1, physics_group)
        physics_layout.addRow("T1_s", self.t1_spin)
        physics_layout.addRow("T2_s", self.t2_spin)
        physics_layout.addRow("M0", self.m0_spin)
        layout.addWidget(physics_group)
        layout.addStretch(1)
        return widget

    def _build_output_tab(self, parent: QWidget) -> QWidget:
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        group = QGroupBox("Output", widget)
        form = QFormLayout(group)
        self.summary_json_edit = QLineEdit(group)
        self.summary_json_edit.setObjectName("experiment-summary-json")
        form.addRow("summary_json", self.summary_json_edit)
        layout.addWidget(group)
        layout.addStretch(1)
        return widget


class _RunBranchEditor(QWidget):
    """Editor for one run branch."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._build_ui()

    def set_run_config(self, run_config: ExperimentRunConfig) -> None:
        """Populate this branch editor from one run config."""
        self.family_combo.setCurrentText(run_config.sequence_family.value)
        self.label_edit.setText(run_config.label)
        if run_config.sequence_family == SequenceFamily.BSSFP and run_config.bssfp is not None:
            self._set_bssfp_config(run_config.bssfp)
        elif run_config.sequence_family == SequenceFamily.FASTSE and run_config.fastse is not None:
            self._set_fastse_config(run_config.fastse)
        elif (
            run_config.sequence_family == SequenceFamily.VFA_FSE
            and run_config.vfa_fse is not None
        ):
            self._set_vfa_config(run_config.vfa_fse)

    def get_run_config(self, *, default_label: str) -> ExperimentRunConfig:
        """Return a validated run config for this branch."""
        family = SequenceFamily(self.family_combo.currentText())
        label = self.label_edit.text().strip() or default_label
        if family == SequenceFamily.BSSFP:
            return ExperimentRunConfig(
                sequence_family=family,
                label=label,
                bssfp=self._get_bssfp_config(default_case_name=label),
            )
        if family == SequenceFamily.FASTSE:
            return ExperimentRunConfig(
                sequence_family=family,
                label=label,
                fastse=self._get_fastse_config(default_case_name=label),
            )
        return ExperimentRunConfig(
            sequence_family=family,
            label=label,
            vfa_fse=self._get_vfa_config(default_case_name=label),
        )

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        header_group = QGroupBox(self._title, self)
        header_layout = QFormLayout(header_group)
        self.family_combo = QComboBox(header_group)
        self.family_combo.addItems([family.value for family in SequenceFamily])
        self.family_combo.setObjectName(f"{self._title.lower().replace(' ', '-')}-family")
        self.label_edit = QLineEdit(header_group)
        header_layout.addRow("sequence_family", self.family_combo)
        header_layout.addRow("label", self.label_edit)
        layout.addWidget(header_group)

        self.stack = QStackedWidget(self)
        self.bssfp_page = self._build_bssfp_page(self.stack)
        self.fastse_page = self._build_fastse_page(self.stack)
        self.vfa_page = self._build_vfa_page(self.stack)
        self.stack.addWidget(self.bssfp_page)
        self.stack.addWidget(self.fastse_page)
        self.stack.addWidget(self.vfa_page)
        layout.addWidget(self.stack)
        layout.addStretch(1)

        self.family_combo.currentTextChanged.connect(self._on_family_changed)
        self._on_family_changed(self.family_combo.currentText())

    def _build_bssfp_page(self, parent: QWidget) -> QWidget:
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        group = QGroupBox("BSSFP", widget)
        form = QFormLayout(group)
        self.bssfp_case_edit = QLineEdit(group)
        self.bssfp_description_edit = QPlainTextEdit(group)
        self.bssfp_description_edit.setMaximumHeight(70)
        self.bssfp_tr_spin = _double_spin(1.0e-6, 10.0, 6, 0.001, group)
        self.bssfp_rf_duration_spin = _double_spin(1.0e-7, 10.0, 6, 0.001, group)
        self.bssfp_n_rf_spin = _int_spin(1, 10000, group)
        self.bssfp_alpha_spin = _double_spin(0.001, 3600.0, 3, 1.0, group)
        self.bssfp_waveform_combo = QComboBox(group)
        self.bssfp_waveform_combo.addItems(["rect", "hann"])
        self.bssfp_readout_fraction_spin = _double_spin(0.0, 1.0, 3, 0.1, group)
        self.bssfp_phase_table = _table(0, ["pulse0_deg", "pulse1_deg"], group)
        self.bssfp_add_phase_button = QPushButton("Add phase row", group)
        self.bssfp_remove_phase_button = QPushButton("Remove phase row", group)
        self.bssfp_delta_start_spin = _double_spin(-1.0e6, 1.0e6, 3, 1.0, group)
        self.bssfp_delta_stop_spin = _double_spin(-1.0e6, 1.0e6, 3, 1.0, group)
        self.bssfp_delta_count_spin = _int_spin(1, 100000, group)
        self.bssfp_rk_method_combo = QComboBox(group)
        self.bssfp_rk_method_combo.addItems(
            ["PROPAGATOR", "RK23", "RK45", "DOP853", "Radau", "BDF", "LSODA"]
        )
        self.bssfp_rk_superperiods_spin = _int_spin(1, 100000, group)
        form.addRow("case_name", self.bssfp_case_edit)
        form.addRow("description", self.bssfp_description_edit)
        form.addRow("TR_s", self.bssfp_tr_spin)
        form.addRow("rf_duration_s", self.bssfp_rf_duration_spin)
        form.addRow("n_rf", self.bssfp_n_rf_spin)
        form.addRow("alpha_deg", self.bssfp_alpha_spin)
        form.addRow("waveform_kind", self.bssfp_waveform_combo)
        form.addRow("readout_fraction_of_free", self.bssfp_readout_fraction_spin)
        form.addRow("phase_cycles", self.bssfp_phase_table)
        phase_buttons = QWidget(group)
        phase_button_layout = QHBoxLayout(phase_buttons)
        phase_button_layout.setContentsMargins(0, 0, 0, 0)
        phase_button_layout.addWidget(self.bssfp_add_phase_button)
        phase_button_layout.addWidget(self.bssfp_remove_phase_button)
        form.addRow("", phase_buttons)
        form.addRow("delta_f_start", self.bssfp_delta_start_spin)
        form.addRow("delta_f_stop", self.bssfp_delta_stop_spin)
        form.addRow("delta_f_count", self.bssfp_delta_count_spin)
        form.addRow("rk_method", self.bssfp_rk_method_combo)
        form.addRow("rk_superperiods", self.bssfp_rk_superperiods_spin)
        layout.addWidget(group)
        self.bssfp_add_phase_button.clicked.connect(
            lambda: _append_table_row(self.bssfp_phase_table, [0.0, 0.0])
        )
        self.bssfp_remove_phase_button.clicked.connect(
            lambda: _remove_last_table_row(self.bssfp_phase_table, minimum_rows=1)
        )
        return widget

    def _build_fastse_page(self, parent: QWidget) -> QWidget:
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        group = QGroupBox("FASTSE_CONST", widget)
        form = QFormLayout(group)
        self.fastse_case_edit = QLineEdit(group)
        self.fastse_description_edit = QPlainTextEdit(group)
        self.fastse_description_edit.setMaximumHeight(70)
        self.fastse_alpha_exc_spin = _double_spin(0.001, 3600.0, 3, 1.0, group)
        self.fastse_phi_exc_spin = _double_spin(-3600.0, 3600.0, 3, 1.0, group)
        self.fastse_alpha_ref_spin = _double_spin(0.001, 3600.0, 3, 1.0, group)
        self.fastse_phi_ref_spin = _double_spin(-3600.0, 3600.0, 3, 1.0, group)
        self.fastse_etl_spin = _int_spin(1, 10000, group)
        self.fastse_esp_spin = _double_spin(1.0e-6, 1.0e6, 3, 1.0, group)
        self.fastse_te_nominal_spin = _double_spin(0.0, 1.0e6, 3, 1.0, group)
        self.fastse_n_iso_spin = _int_spin(1, 100000, group)
        self.fastse_off_res_spin = _double_spin(-1.0e6, 1.0e6, 3, 1.0, group)
        form.addRow("case_name", self.fastse_case_edit)
        form.addRow("description", self.fastse_description_edit)
        form.addRow("alpha_exc_deg", self.fastse_alpha_exc_spin)
        form.addRow("phi_exc_deg", self.fastse_phi_exc_spin)
        form.addRow("alpha_ref_const_deg", self.fastse_alpha_ref_spin)
        form.addRow("phi_ref_deg", self.fastse_phi_ref_spin)
        form.addRow("etl", self.fastse_etl_spin)
        form.addRow("esp_ms", self.fastse_esp_spin)
        form.addRow("te_nominal_ms (0 = none)", self.fastse_te_nominal_spin)
        form.addRow("n_iso", self.fastse_n_iso_spin)
        form.addRow("off_resonance_hz", self.fastse_off_res_spin)
        layout.addWidget(group)
        return widget

    def _build_vfa_page(self, parent: QWidget) -> QWidget:
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        group = QGroupBox("VFA_FSE_MANUAL", widget)
        form = QFormLayout(group)
        self.vfa_case_edit = QLineEdit(group)
        self.vfa_description_edit = QPlainTextEdit(group)
        self.vfa_description_edit.setMaximumHeight(70)
        self.vfa_alpha_exc_spin = _double_spin(0.001, 3600.0, 3, 1.0, group)
        self.vfa_phi_exc_spin = _double_spin(-3600.0, 3600.0, 3, 1.0, group)
        self.vfa_train_table = _table(0, ["alpha_ref_deg", "phi_ref_deg"], group)
        self.vfa_add_train_button = QPushButton("Add train row", group)
        self.vfa_remove_train_button = QPushButton("Remove train row", group)
        self.vfa_explicit_phase_check = QCheckBox("Use explicit phase train", group)
        self.vfa_esp_spin = _double_spin(1.0e-6, 1.0e6, 3, 1.0, group)
        self.vfa_te_nominal_spin = _double_spin(0.0, 1.0e6, 3, 1.0, group)
        self.vfa_n_iso_spin = _int_spin(1, 100000, group)
        self.vfa_off_res_spin = _double_spin(-1.0e6, 1.0e6, 3, 1.0, group)
        note = QLabel("B2006/B2008 generators are not implemented in this phase.", group)
        note.setWordWrap(True)
        form.addRow("case_name", self.vfa_case_edit)
        form.addRow("description", self.vfa_description_edit)
        form.addRow("alpha_exc_deg", self.vfa_alpha_exc_spin)
        form.addRow("phi_exc_deg", self.vfa_phi_exc_spin)
        form.addRow("refocusing train", self.vfa_train_table)
        buttons = QWidget(group)
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(self.vfa_add_train_button)
        buttons_layout.addWidget(self.vfa_remove_train_button)
        form.addRow("", buttons)
        form.addRow(self.vfa_explicit_phase_check)
        form.addRow("esp_ms", self.vfa_esp_spin)
        form.addRow("te_nominal_ms (0 = none)", self.vfa_te_nominal_spin)
        form.addRow("n_iso", self.vfa_n_iso_spin)
        form.addRow("off_resonance_hz", self.vfa_off_res_spin)
        form.addRow("note", note)
        layout.addWidget(group)
        self.vfa_add_train_button.clicked.connect(
            lambda: _append_table_row(self.vfa_train_table, [180.0, 90.0])
        )
        self.vfa_remove_train_button.clicked.connect(
            lambda: _remove_last_table_row(self.vfa_train_table, minimum_rows=1)
        )
        return widget

    def _on_family_changed(self, family_text: str) -> None:
        family = SequenceFamily(family_text)
        index = {
            SequenceFamily.BSSFP: 0,
            SequenceFamily.FASTSE: 1,
            SequenceFamily.VFA_FSE: 2,
        }[family]
        self.stack.setCurrentIndex(index)

    def _set_bssfp_config(self, config: BSSFPFamilyConfig) -> None:
        self.bssfp_case_edit.setText(config.case_name)
        self.bssfp_description_edit.setPlainText(config.description)
        self.bssfp_tr_spin.setValue(config.sequence.tr_s)
        self.bssfp_rf_duration_spin.setValue(config.sequence.rf_duration_s)
        self.bssfp_n_rf_spin.setValue(config.sequence.n_rf)
        self.bssfp_alpha_spin.setValue(config.sequence.alpha_deg)
        self.bssfp_waveform_combo.setCurrentText(config.sequence.waveform_kind)
        self.bssfp_readout_fraction_spin.setValue(config.sequence.readout_fraction_of_free)
        _set_table_rows(self.bssfp_phase_table, config.phase_cycles.values_deg)
        self.bssfp_delta_start_spin.setValue(config.sweep.start_hz)
        self.bssfp_delta_stop_spin.setValue(config.sweep.stop_hz)
        self.bssfp_delta_count_spin.setValue(config.sweep.count)
        self.bssfp_rk_method_combo.setCurrentText(config.integration.rk_method)
        self.bssfp_rk_superperiods_spin.setValue(config.integration.rk_superperiods)

    def _set_fastse_config(self, config: FastSEFamilyConfig) -> None:
        self.fastse_case_edit.setText(config.case_name)
        self.fastse_description_edit.setPlainText(config.description)
        self.fastse_alpha_exc_spin.setValue(config.alpha_exc_deg)
        self.fastse_phi_exc_spin.setValue(config.phi_exc_deg)
        self.fastse_alpha_ref_spin.setValue(config.alpha_ref_const_deg)
        self.fastse_phi_ref_spin.setValue(config.phi_ref_deg)
        self.fastse_etl_spin.setValue(config.etl)
        self.fastse_esp_spin.setValue(config.esp_ms)
        self.fastse_te_nominal_spin.setValue(config.te_nominal_ms or 0.0)
        self.fastse_n_iso_spin.setValue(config.n_iso)
        self.fastse_off_res_spin.setValue(config.off_resonance_hz)

    def _set_vfa_config(self, config: VFAFSEFamilyConfig) -> None:
        self.vfa_case_edit.setText(config.case_name)
        self.vfa_description_edit.setPlainText(config.description)
        self.vfa_alpha_exc_spin.setValue(config.alpha_exc_deg)
        self.vfa_phi_exc_spin.setValue(config.phi_exc_deg)
        assert config.phi_ref_train_deg is not None
        _set_table_rows(
            self.vfa_train_table,
            np.column_stack((config.alpha_ref_train_deg, config.phi_ref_train_deg)),
        )
        self.vfa_explicit_phase_check.setChecked(True)
        self.vfa_esp_spin.setValue(config.esp_ms)
        self.vfa_te_nominal_spin.setValue(config.te_nominal_ms or 0.0)
        self.vfa_n_iso_spin.setValue(config.n_iso)
        self.vfa_off_res_spin.setValue(config.off_resonance_hz)

    def _get_bssfp_config(self, *, default_case_name: str) -> BSSFPFamilyConfig:
        phase_values = _table_values(self.bssfp_phase_table, min_columns=2)
        return BSSFPFamilyConfig(
            case_name=self.bssfp_case_edit.text().strip() or default_case_name,
            description=self.bssfp_description_edit.toPlainText().strip(),
            sequence=SequenceConfig(
                tr_s=self.bssfp_tr_spin.value(),
                rf_duration_s=self.bssfp_rf_duration_spin.value(),
                n_rf=self.bssfp_n_rf_spin.value(),
                alpha_deg=self.bssfp_alpha_spin.value(),
                waveform_kind=self.bssfp_waveform_combo.currentText(),
                readout_fraction_of_free=self.bssfp_readout_fraction_spin.value(),
            ),
            phase_cycles=PhaseCycleConfig(values_deg=phase_values),
            sweep=SweepConfig(
                start_hz=self.bssfp_delta_start_spin.value(),
                stop_hz=self.bssfp_delta_stop_spin.value(),
                count=self.bssfp_delta_count_spin.value(),
            ),
            integration=IntegrationConfig(
                rk_method=self.bssfp_rk_method_combo.currentText(),
                rk_superperiods=self.bssfp_rk_superperiods_spin.value(),
            ),
            output=OutputConfig(),
        )

    def _get_fastse_config(self, *, default_case_name: str) -> FastSEFamilyConfig:
        te_nominal = self.fastse_te_nominal_spin.value()
        return FastSEFamilyConfig(
            case_name=self.fastse_case_edit.text().strip() or default_case_name,
            description=self.fastse_description_edit.toPlainText().strip(),
            alpha_exc_deg=self.fastse_alpha_exc_spin.value(),
            phi_exc_deg=self.fastse_phi_exc_spin.value(),
            alpha_ref_const_deg=self.fastse_alpha_ref_spin.value(),
            phi_ref_deg=self.fastse_phi_ref_spin.value(),
            etl=self.fastse_etl_spin.value(),
            esp_ms=self.fastse_esp_spin.value(),
            te_nominal_ms=None if te_nominal <= 0.0 else te_nominal,
            n_iso=self.fastse_n_iso_spin.value(),
            off_resonance_hz=self.fastse_off_res_spin.value(),
        )

    def _get_vfa_config(self, *, default_case_name: str) -> VFAFSEFamilyConfig:
        train_values = _table_values(self.vfa_train_table, min_columns=2)
        te_nominal = self.vfa_te_nominal_spin.value()
        return VFAFSEFamilyConfig(
            case_name=self.vfa_case_edit.text().strip() or default_case_name,
            description=self.vfa_description_edit.toPlainText().strip(),
            alpha_exc_deg=self.vfa_alpha_exc_spin.value(),
            phi_exc_deg=self.vfa_phi_exc_spin.value(),
            alpha_ref_train_deg=train_values[:, 0],
            phi_ref_train_deg=(
                train_values[:, 1] if self.vfa_explicit_phase_check.isChecked() else None
            ),
            esp_ms=self.vfa_esp_spin.value(),
            te_nominal_ms=None if te_nominal <= 0.0 else te_nominal,
            n_iso=self.vfa_n_iso_spin.value(),
            off_resonance_hz=self.vfa_off_res_spin.value(),
        )


def make_default_experiment_config() -> ExperimentConfig:
    """Return a small editable default config for the generic viewer."""
    return ExperimentConfig(
        comparison_scope="physics_only",
        comparison_modes=("matched_TE_contrast",),
        common_physics=CommonPhysicsConfig(t1_s=1.2, t2_s=0.08, m0=1.0),
        run_a=ExperimentRunConfig(
            sequence_family=SequenceFamily.FASTSE,
            label="fastse_low_flip",
            fastse=FastSEFamilyConfig(
                case_name="fastse_low_flip",
                description="Constant-low-flip Fast SE baseline",
                alpha_exc_deg=90.0,
                phi_exc_deg=0.0,
                alpha_ref_const_deg=120.0,
                phi_ref_deg=90.0,
                etl=4,
                esp_ms=8.0,
                te_nominal_ms=16.0,
                n_iso=101,
                off_resonance_hz=0.0,
            ),
        ),
        run_b=ExperimentRunConfig(
            sequence_family=SequenceFamily.VFA_FSE,
            label="vfa_manual",
            vfa_fse=VFAFSEFamilyConfig(
                case_name="vfa_manual",
                description="Manual VFA-FSE baseline",
                alpha_exc_deg=90.0,
                phi_exc_deg=0.0,
                alpha_ref_train_deg=np.asarray([150.0, 130.0, 110.0, 90.0]),
                phi_ref_train_deg=np.asarray([90.0, 100.0, 110.0, 120.0]),
                esp_ms=8.0,
                te_nominal_ms=16.0,
                n_iso=101,
                off_resonance_hz=0.0,
            ),
        ),
    )


def _double_spin(
    minimum: float,
    maximum: float,
    decimals: int,
    step: float,
    parent: QWidget,
) -> QDoubleSpinBox:
    spin = QDoubleSpinBox(parent)
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setSingleStep(step)
    return spin


def _int_spin(minimum: int, maximum: int, parent: QWidget) -> QSpinBox:
    spin = QSpinBox(parent)
    spin.setRange(minimum, maximum)
    return spin


def _table(rows: int, headers: list[str], parent: QWidget) -> QTableWidget:
    table = QTableWidget(rows, len(headers), parent)
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setStretchLastSection(True)
    table.verticalHeader().setVisible(False)
    table.setMinimumHeight(110)
    return table


def _append_table_row(table: QTableWidget, values: list[float]) -> None:
    row = table.rowCount()
    table.insertRow(row)
    for column, value in enumerate(values):
        table.setItem(row, column, QTableWidgetItem(f"{float(value):.6g}"))


def _remove_last_table_row(table: QTableWidget, *, minimum_rows: int) -> None:
    if table.rowCount() > minimum_rows:
        table.removeRow(table.rowCount() - 1)


def _set_table_rows(table: QTableWidget, values: np.ndarray) -> None:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim == 1:
        array = array.reshape((-1, 1))
    table.setRowCount(0)
    for row_values in array:
        _append_table_row(table, [float(value) for value in row_values])


def _table_values(table: QTableWidget, *, min_columns: int) -> np.ndarray:
    if table.rowCount() == 0:
        msg = "Table must contain at least one row."
        raise ValueError(msg)
    values = np.zeros((table.rowCount(), min_columns), dtype=np.float64)
    for row in range(table.rowCount()):
        for column in range(min_columns):
            item = table.item(row, column)
            if item is None or not item.text().strip():
                msg = f"Missing numeric value at row {row + 1}, column {column + 1}."
                raise ValueError(msg)
            values[row, column] = float(item.text())
    return values

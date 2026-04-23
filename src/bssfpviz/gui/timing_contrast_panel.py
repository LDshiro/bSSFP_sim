"""Timing and contrast inspector for the generic preview shell."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bssfpviz.gui.preview_view_models import (
    TimingContrastComparisonViewModel,
    TimingContrastViewModel,
)


class TimingContrastPanel(QWidget):
    """Read-only timing and contrast panel with A/B side-by-side tables."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model: TimingContrastComparisonViewModel | None = None
        self._build_ui()
        self.clear()

    def clear(self) -> None:
        """Reset the panel to its empty state."""
        self._model = None
        self.run_a_header_label.setText("Run A")
        self.run_b_header_label.setText("Run B")
        self.run_a_warning_label.setText("Warnings:\n-")
        self.run_b_warning_label.setText("Warnings:\n-")
        self.note_label.setText("Load an Experiment YAML to inspect timing and contrast.")
        self._clear_table(self.run_a_table)
        self._clear_table(self.run_b_table)
        self._clear_table(self.delta_table)

    def set_comparison_view_model(self, model: TimingContrastComparisonViewModel) -> None:
        """Render one full side-by-side comparison preview."""
        self._model = model
        self._populate_run_section(
            header_label=self.run_a_header_label,
            warning_label=self.run_a_warning_label,
            table=self.run_a_table,
            view_model=model.run_a,
        )
        self._populate_run_section(
            header_label=self.run_b_header_label,
            warning_label=self.run_b_warning_label,
            table=self.run_b_table,
            view_model=model.run_b,
        )
        self._populate_delta_table(model)
        self.note_label.setText(model.note_text)

    def get_run_value_text(self, run_slot: str, key: str) -> str:
        """Return the displayed text for one run-row key."""
        if self._model is None:
            msg = "No timing/contrast preview is loaded."
            raise ValueError(msg)
        if run_slot == "run_a":
            return self._model.run_a.value_text_for_key(key)
        if run_slot == "run_b":
            return self._model.run_b.value_text_for_key(key)
        msg = f"Unsupported run slot: {run_slot}"
        raise ValueError(msg)

    def get_delta_value_text(self, key: str) -> str:
        """Return the displayed text for one delta metric."""
        if self._model is None:
            msg = "No timing/contrast preview is loaded."
            raise ValueError(msg)
        return self._model.delta_value_text_for_key(key)

    def _build_ui(self) -> None:
        self.setObjectName("timing-contrast-panel")
        root_layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        root_layout.addLayout(top_layout, 1)

        run_a_group = QGroupBox("Run A", self)
        run_a_layout = QVBoxLayout(run_a_group)
        self.run_a_header_label = QLabel(run_a_group)
        self.run_a_header_label.setObjectName("timing-run-a-header")
        self.run_a_header_label.setWordWrap(True)
        self.run_a_table = self._make_table(run_a_group, "timing-run-a-table")
        self.run_a_warning_label = QLabel(run_a_group)
        self.run_a_warning_label.setObjectName("timing-run-a-warnings")
        self.run_a_warning_label.setWordWrap(True)
        self.run_a_warning_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        run_a_layout.addWidget(self.run_a_header_label)
        run_a_layout.addWidget(self.run_a_table, 1)
        run_a_layout.addWidget(self.run_a_warning_label)
        top_layout.addWidget(run_a_group, 1)

        run_b_group = QGroupBox("Run B", self)
        run_b_layout = QVBoxLayout(run_b_group)
        self.run_b_header_label = QLabel(run_b_group)
        self.run_b_header_label.setObjectName("timing-run-b-header")
        self.run_b_header_label.setWordWrap(True)
        self.run_b_table = self._make_table(run_b_group, "timing-run-b-table")
        self.run_b_warning_label = QLabel(run_b_group)
        self.run_b_warning_label.setObjectName("timing-run-b-warnings")
        self.run_b_warning_label.setWordWrap(True)
        self.run_b_warning_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        run_b_layout.addWidget(self.run_b_header_label)
        run_b_layout.addWidget(self.run_b_table, 1)
        run_b_layout.addWidget(self.run_b_warning_label)
        top_layout.addWidget(run_b_group, 1)

        delta_group = QGroupBox("Comparison Strip", self)
        delta_layout = QVBoxLayout(delta_group)
        self.delta_table = self._make_table(delta_group, "timing-delta-table")
        self.note_label = QLabel(delta_group)
        self.note_label.setObjectName("timing-note-label")
        self.note_label.setWordWrap(True)
        delta_layout.addWidget(self.delta_table)
        delta_layout.addWidget(self.note_label)
        root_layout.addWidget(delta_group)

    def _populate_run_section(
        self,
        *,
        header_label: QLabel,
        warning_label: QLabel,
        table: QTableWidget,
        view_model: TimingContrastViewModel,
    ) -> None:
        header_label.setText(
            f"{view_model.sequence_family} | {view_model.run_label} | {view_model.case_name}"
        )
        warning_lines = ["Warnings:"]
        if view_model.warnings:
            warning_lines.extend(f"- {warning}" for warning in view_model.warnings)
        else:
            warning_lines.append("- none")
        warning_label.setText("\n".join(warning_lines))

        table.setRowCount(len(view_model.rows))
        for row_index, row in enumerate(view_model.rows):
            metric_item = QTableWidgetItem(row.label)
            value_item = QTableWidgetItem(row.value_text)
            if row.is_primary:
                font = QFont(metric_item.font())
                font.setBold(True)
                metric_item.setFont(font)
                value_item.setFont(font)
            self._finalize_item(metric_item)
            self._finalize_item(value_item)
            table.setItem(row_index, 0, metric_item)
            table.setItem(row_index, 1, value_item)
        table.resizeColumnsToContents()

    def _populate_delta_table(self, model: TimingContrastComparisonViewModel) -> None:
        self.delta_table.setRowCount(len(model.delta_rows))
        for row_index, row in enumerate(model.delta_rows):
            metric_item = QTableWidgetItem(row.label)
            value_item = QTableWidgetItem(row.value_text)
            if row.highlight:
                font = QFont(metric_item.font())
                font.setBold(True)
                metric_item.setFont(font)
                value_item.setFont(font)
            self._finalize_item(metric_item)
            self._finalize_item(value_item)
            self.delta_table.setItem(row_index, 0, metric_item)
            self.delta_table.setItem(row_index, 1, value_item)
        self.delta_table.resizeColumnsToContents()

    def _clear_table(self, table: QTableWidget) -> None:
        table.setRowCount(0)
        table.clearContents()

    def _make_table(self, parent: QWidget, object_name: str) -> QTableWidget:
        table = QTableWidget(parent)
        table.setObjectName(object_name)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Metric", "Value"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return table

    @staticmethod
    def _finalize_item(item: QTableWidgetItem) -> None:
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)

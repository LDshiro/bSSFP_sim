"""Bundle comparison summary panel for the generic inspector shell."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bssfpviz.gui.bundle_view_models import ComparisonSectionViewModel, ComparisonSummaryViewModel


class ComparisonSummaryPanel(QWidget):
    """Read-only panel that renders matched constraints, ratios, and report metadata."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model: ComparisonSummaryViewModel | None = None
        self._build_ui()
        self.clear()

    def clear(self) -> None:
        """Reset the panel to its empty state."""
        self._model = None
        self._clear_table(self.matched_table)
        self._clear_table(self.ratio_table)
        self._clear_table(self.report_table)
        self.note_label.setText("Load a comparison bundle to inspect summary metrics.")

    def set_view_model(self, model: ComparisonSummaryViewModel) -> None:
        """Render one comparison summary."""
        self._model = model
        self._populate_section(self.matched_group, self.matched_table, model.matched_constraints)
        self._populate_section(self.ratio_group, self.ratio_table, model.derived_ratios)
        self._populate_section(self.report_group, self.report_table, model.report_metadata)
        self.note_label.setText(model.note_text)

    def get_value_text(self, section_key: str, key: str) -> str:
        """Return one rendered value for test inspection."""
        if self._model is None:
            msg = "No comparison summary is loaded."
            raise ValueError(msg)
        section = self._section_for_key(section_key)
        return section.value_text_for_key(key)

    def is_highlighted(self, section_key: str, key: str) -> bool:
        """Return whether one row is emphasized."""
        if self._model is None:
            msg = "No comparison summary is loaded."
            raise ValueError(msg)
        section = self._section_for_key(section_key)
        return section.highlight_for_key(key)

    def _section_for_key(self, section_key: str) -> ComparisonSectionViewModel:
        if self._model is None:
            msg = "No comparison summary is loaded."
            raise ValueError(msg)
        if section_key == "matched_constraints":
            return self._model.matched_constraints
        if section_key == "derived_ratios":
            return self._model.derived_ratios
        if section_key == "report_metadata":
            return self._model.report_metadata
        msg = f"Unsupported section key: {section_key}"
        raise ValueError(msg)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.matched_group = QGroupBox("Matched Constraints", self)
        matched_layout = QVBoxLayout(self.matched_group)
        self.matched_table = self._make_table(self.matched_group, "comparison-matched-table")
        matched_layout.addWidget(self.matched_table)
        layout.addWidget(self.matched_group)

        self.ratio_group = QGroupBox("Derived Ratios", self)
        ratio_layout = QVBoxLayout(self.ratio_group)
        self.ratio_table = self._make_table(self.ratio_group, "comparison-ratio-table")
        ratio_layout.addWidget(self.ratio_table)
        layout.addWidget(self.ratio_group)

        self.report_group = QGroupBox("Report Metadata", self)
        report_layout = QVBoxLayout(self.report_group)
        self.report_table = self._make_table(self.report_group, "comparison-report-table")
        report_layout.addWidget(self.report_table)
        layout.addWidget(self.report_group)

        self.note_label = QLabel(self)
        self.note_label.setObjectName("comparison-summary-note")
        self.note_label.setWordWrap(True)
        layout.addWidget(self.note_label)
        layout.addStretch(1)

    def _populate_section(
        self,
        group: QGroupBox,
        table: QTableWidget,
        section: ComparisonSectionViewModel,
    ) -> None:
        group.setTitle(section.title)
        table.setRowCount(len(section.rows))
        for row_index, row in enumerate(section.rows):
            metric_item = QTableWidgetItem(row.label)
            value_item = QTableWidgetItem(row.value_text)
            if row.highlight:
                font = QFont(metric_item.font())
                font.setBold(True)
                metric_item.setFont(font)
                value_item.setFont(font)
                metric_item.setBackground(QColor("#ffe3e3"))
                value_item.setBackground(QColor("#ffe3e3"))
            self._finalize_item(metric_item)
            self._finalize_item(value_item)
            table.setItem(row_index, 0, metric_item)
            table.setItem(row_index, 1, value_item)
        table.resizeColumnsToContents()

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

    def _clear_table(self, table: QTableWidget) -> None:
        table.setRowCount(0)
        table.clearContents()

    @staticmethod
    def _finalize_item(item: QTableWidgetItem) -> None:
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)

"""Sequence preview inspector for the generic preview shell."""

from __future__ import annotations

from PySide6.QtCore import Qt
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
    SequenceComparisonViewModel,
    SequenceRunViewModel,
    SequenceSummaryRow,
    SequenceTableSection,
)


class SequencePanel(QWidget):
    """Read-only sequence preview panel with A/B side-by-side sections."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model: SequenceComparisonViewModel | None = None
        self._build_ui()
        self.clear()

    def clear(self) -> None:
        """Reset the panel to its empty state."""
        self._model = None
        self.run_a_widget.clear()
        self.run_b_widget.clear()
        self.note_label.setText("Load an Experiment YAML to inspect the sequence preview.")
        self._clear_table(self.delta_table)

    def set_comparison_view_model(self, model: SequenceComparisonViewModel) -> None:
        """Render one full side-by-side sequence preview."""
        self._model = model
        self.run_a_widget.set_view_model(model.run_a)
        self.run_b_widget.set_view_model(model.run_b)
        self.delta_table.setRowCount(len(model.delta_rows))
        for row_index, row in enumerate(model.delta_rows):
            metric_item = QTableWidgetItem(row.label)
            value_item = QTableWidgetItem(row.value_text)
            self._finalize_item(metric_item)
            self._finalize_item(value_item)
            self.delta_table.setItem(row_index, 0, metric_item)
            self.delta_table.setItem(row_index, 1, value_item)
        self.delta_table.resizeColumnsToContents()
        self.note_label.setText(model.note_text)

    def get_run_summary_value_text(self, run_slot: str, key: str) -> str:
        """Return one rendered summary row from the current model."""
        if self._model is None:
            msg = "No sequence preview is loaded."
            raise ValueError(msg)
        if run_slot == "run_a":
            return self._model.run_a.summary_value_text_for_key(key)
        if run_slot == "run_b":
            return self._model.run_b.summary_value_text_for_key(key)
        msg = f"Unsupported run slot: {run_slot}"
        raise ValueError(msg)

    def get_run_table_cell_text(
        self,
        run_slot: str,
        table_key: str,
        row_index: int,
        column_index: int,
    ) -> str:
        """Return one rendered table cell from the current model."""
        if self._model is None:
            msg = "No sequence preview is loaded."
            raise ValueError(msg)
        if run_slot == "run_a":
            return self._model.run_a.table_cell_text(table_key, row_index, column_index)
        if run_slot == "run_b":
            return self._model.run_b.table_cell_text(table_key, row_index, column_index)
        msg = f"Unsupported run slot: {run_slot}"
        raise ValueError(msg)

    def get_delta_value_text(self, key: str) -> str:
        """Return one rendered comparison-strip value."""
        if self._model is None:
            msg = "No sequence preview is loaded."
            raise ValueError(msg)
        return self._model.delta_value_text_for_key(key)

    def _build_ui(self) -> None:
        self.setObjectName("sequence-panel")
        root_layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        root_layout.addLayout(top_layout, 1)

        self.run_a_widget = _RunSequenceWidget("Run A", self)
        self.run_a_widget.setObjectName("sequence-run-a-widget")
        top_layout.addWidget(self.run_a_widget, 1)

        self.run_b_widget = _RunSequenceWidget("Run B", self)
        self.run_b_widget.setObjectName("sequence-run-b-widget")
        top_layout.addWidget(self.run_b_widget, 1)

        delta_group = QGroupBox("Comparison Strip", self)
        delta_layout = QVBoxLayout(delta_group)
        self.delta_table = self._make_table(delta_group, "sequence-delta-table", columns=2)
        self.delta_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.note_label = QLabel(delta_group)
        self.note_label.setObjectName("sequence-note-label")
        self.note_label.setWordWrap(True)
        delta_layout.addWidget(self.delta_table)
        delta_layout.addWidget(self.note_label)
        root_layout.addWidget(delta_group)

    def _clear_table(self, table: QTableWidget) -> None:
        table.setRowCount(0)
        table.clearContents()

    def _make_table(
        self,
        parent: QWidget,
        object_name: str,
        *,
        columns: int,
    ) -> QTableWidget:
        table = QTableWidget(parent)
        table.setObjectName(object_name)
        table.setColumnCount(columns)
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


class _RunSequenceWidget(QGroupBox):
    """One run-side sequence preview widget."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._build_ui()

    def clear(self) -> None:
        """Reset the widget to its empty state."""
        self.header_label.setText(self.title())
        self.primary_group.setTitle("Primary Table")
        self.secondary_group.setTitle("Secondary Table")
        self.summary_group.setTitle("Summary")
        self.extra_summary_group.setTitle("Extra Summary")
        self.warning_label.setText("Warnings:\n-")
        self._clear_table(self.primary_table)
        self._clear_table(self.secondary_table)
        self._clear_table(self.summary_table)
        self._clear_table(self.extra_summary_table)
        self.secondary_group.hide()
        self.extra_summary_group.hide()

    def set_view_model(self, model: SequenceRunViewModel) -> None:
        """Render one run-side sequence preview."""
        self.header_label.setText(
            f"{model.sequence_family} | {model.run_label} | {model.case_name}"
        )
        self._populate_table_section(
            group=self.primary_group,
            table=self.primary_table,
            section=model.primary_table,
        )
        self._populate_table_section(
            group=self.secondary_group,
            table=self.secondary_table,
            section=model.secondary_table,
        )
        self._populate_summary_table(
            group=self.summary_group,
            table=self.summary_table,
            title=model.summary_title,
            rows=model.summary_rows,
        )
        self._populate_summary_table(
            group=self.extra_summary_group,
            table=self.extra_summary_table,
            title=model.extra_summary_title or "Extra Summary",
            rows=model.extra_summary_rows,
        )

        warning_lines = ["Warnings:"]
        if model.warnings:
            warning_lines.extend(f"- {warning}" for warning in model.warnings)
        else:
            warning_lines.append("- none")
        self.warning_label.setText("\n".join(warning_lines))

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.header_label = QLabel(self)
        self.header_label.setObjectName("sequence-run-header")
        self.header_label.setWordWrap(True)
        layout.addWidget(self.header_label)

        self.primary_group = QGroupBox("Primary Table", self)
        primary_layout = QVBoxLayout(self.primary_group)
        self.primary_table = self._make_table(self.primary_group, "sequence-primary-table", 3)
        primary_layout.addWidget(self.primary_table)
        layout.addWidget(self.primary_group)

        self.secondary_group = QGroupBox("Secondary Table", self)
        secondary_layout = QVBoxLayout(self.secondary_group)
        self.secondary_table = self._make_table(self.secondary_group, "sequence-secondary-table", 3)
        secondary_layout.addWidget(self.secondary_table)
        layout.addWidget(self.secondary_group)

        self.summary_group = QGroupBox("Summary", self)
        summary_layout = QVBoxLayout(self.summary_group)
        self.summary_table = self._make_table(self.summary_group, "sequence-summary-table", 2)
        self.summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
        summary_layout.addWidget(self.summary_table)
        layout.addWidget(self.summary_group)

        self.extra_summary_group = QGroupBox("Extra Summary", self)
        extra_summary_layout = QVBoxLayout(self.extra_summary_group)
        self.extra_summary_table = self._make_table(
            self.extra_summary_group,
            "sequence-extra-summary-table",
            2,
        )
        self.extra_summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
        extra_summary_layout.addWidget(self.extra_summary_table)
        layout.addWidget(self.extra_summary_group)

        self.warning_label = QLabel(self)
        self.warning_label.setObjectName("sequence-run-warnings")
        self.warning_label.setWordWrap(True)
        self.warning_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.warning_label)
        layout.addStretch(1)

    def _populate_table_section(
        self,
        *,
        group: QGroupBox,
        table: QTableWidget,
        section: SequenceTableSection | None,
    ) -> None:
        if section is None:
            group.hide()
            self._clear_table(table)
            return
        group.show()
        group.setTitle(section.title)
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(list(section.column_labels))
        table.setRowCount(len(section.rows))
        for row_index, row in enumerate(section.rows):
            for column_index, value_text in enumerate(
                (row.index_text, row.value_a_text, row.value_b_text)
            ):
                item = QTableWidgetItem(value_text)
                self._finalize_item(item)
                table.setItem(row_index, column_index, item)
        table.resizeColumnsToContents()

    def _populate_summary_table(
        self,
        *,
        group: QGroupBox,
        table: QTableWidget,
        title: str,
        rows: tuple[SequenceSummaryRow, ...],
    ) -> None:
        if len(rows) == 0:
            group.hide()
            self._clear_table(table)
            return
        group.show()
        group.setTitle(title)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Metric", "Value"])
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            metric_item = QTableWidgetItem(row.label)
            value_item = QTableWidgetItem(row.value_text)
            self._finalize_item(metric_item)
            self._finalize_item(value_item)
            table.setItem(row_index, 0, metric_item)
            table.setItem(row_index, 1, value_item)
        table.resizeColumnsToContents()

    def _clear_table(self, table: QTableWidget) -> None:
        table.setRowCount(0)
        table.clearContents()

    def _make_table(self, parent: QWidget, object_name: str, columns: int) -> QTableWidget:
        table = QTableWidget(parent)
        table.setObjectName(object_name)
        table.setColumnCount(columns)
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

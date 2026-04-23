"""Bundle-driven results inspector for the generic comparison shell."""

from __future__ import annotations

import pyqtgraph as pg
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

from bssfpviz.gui.bundle_view_models import (
    PlotSeries,
    ResultsComparisonViewModel,
    ResultsRunViewModel,
)


class ResultsPanel(QWidget):
    """Read-only bundle results panel with A/B side-by-side plots."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model: ResultsComparisonViewModel | None = None
        self._build_ui()
        self.clear()

    def clear(self) -> None:
        """Reset the panel to its empty state."""
        self._model = None
        self.run_a_widget.clear()
        self.run_b_widget.clear()
        self.note_label.setText("Load a comparison bundle to inspect results.")
        self._clear_table(self.delta_table)

    def set_comparison_view_model(self, model: ResultsComparisonViewModel) -> None:
        """Render one bundle-driven results comparison."""
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
        """Return one rendered summary value for test inspection."""
        if self._model is None:
            msg = "No bundle results are loaded."
            raise ValueError(msg)
        if run_slot == "run_a":
            return self._model.run_a.summary_value_text_for_key(key)
        if run_slot == "run_b":
            return self._model.run_b.summary_value_text_for_key(key)
        msg = f"Unsupported run slot: {run_slot}"
        raise ValueError(msg)

    def get_delta_value_text(self, key: str) -> str:
        """Return one rendered delta value for test inspection."""
        if self._model is None:
            msg = "No bundle results are loaded."
            raise ValueError(msg)
        return self._model.delta_value_text_for_key(key)

    def get_run_curve_count(self, run_slot: str, plot_key: str) -> int:
        """Return the number of plotted line series for one run plot."""
        if run_slot == "run_a":
            return self.run_a_widget.curve_count(plot_key)
        if run_slot == "run_b":
            return self.run_b_widget.curve_count(plot_key)
        msg = f"Unsupported run slot: {run_slot}"
        raise ValueError(msg)

    def _build_ui(self) -> None:
        self.setObjectName("results-panel")
        root_layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        root_layout.addLayout(top_layout, 1)

        self.run_a_widget = _RunResultsWidget("Run A", self)
        self.run_a_widget.setObjectName("results-run-a-widget")
        top_layout.addWidget(self.run_a_widget, 1)

        self.run_b_widget = _RunResultsWidget("Run B", self)
        self.run_b_widget.setObjectName("results-run-b-widget")
        top_layout.addWidget(self.run_b_widget, 1)

        delta_group = QGroupBox("Comparison Strip", self)
        delta_layout = QVBoxLayout(delta_group)
        self.delta_table = self._make_table(delta_group, "results-delta-table")
        self.note_label = QLabel(delta_group)
        self.note_label.setObjectName("results-note-label")
        self.note_label.setWordWrap(True)
        delta_layout.addWidget(self.delta_table)
        delta_layout.addWidget(self.note_label)
        root_layout.addWidget(delta_group)

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


class _RunResultsWidget(QGroupBox):
    """One run-side plotting widget inside the results tab."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._build_ui()

    def clear(self) -> None:
        """Reset the widget to its empty state."""
        self.header_label.setText(self.title())
        self.primary_group.setTitle("Primary Plot")
        self.secondary_group.setTitle("Secondary Plot")
        self.summary_group.setTitle("Summary")
        self.extra_summary_group.setTitle("Extra Summary")
        self._clear_plot(self.primary_plot)
        self._clear_plot(self.secondary_plot)
        self._clear_table(self.summary_table)
        self._clear_table(self.extra_summary_table)
        self.secondary_group.hide()
        self.extra_summary_group.hide()

    def set_view_model(self, model: ResultsRunViewModel) -> None:
        """Render one run-side bundle result view."""
        self.header_label.setText(
            f"{model.sequence_family} | {model.run_label} | {model.case_name}"
        )
        self._populate_plot(
            group=self.primary_group,
            plot=self.primary_plot,
            title=model.primary_plot_title,
            x_label=model.primary_x_label,
            y_label=model.primary_y_label,
            series=model.primary_series,
        )
        if len(model.secondary_series) == 0 or model.secondary_plot_title is None:
            self.secondary_group.hide()
            self._clear_plot(self.secondary_plot)
        else:
            self.secondary_group.show()
            self._populate_plot(
                group=self.secondary_group,
                plot=self.secondary_plot,
                title=model.secondary_plot_title,
                x_label=model.secondary_x_label or "",
                y_label=model.secondary_y_label or "",
                series=model.secondary_series,
            )
        self._populate_summary_table(
            self.summary_group,
            self.summary_table,
            "Summary",
            model.summary_rows,
        )
        self._populate_summary_table(
            self.extra_summary_group,
            self.extra_summary_table,
            "Extra Summary",
            model.extra_summary_rows,
        )

    def curve_count(self, plot_key: str) -> int:
        """Return the plotted curve count for one plot slot."""
        if plot_key == "primary":
            return len(self.primary_plot.getPlotItem().listDataItems())
        if plot_key == "secondary":
            return len(self.secondary_plot.getPlotItem().listDataItems())
        msg = f"Unsupported plot key: {plot_key}"
        raise ValueError(msg)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.header_label = QLabel(self)
        self.header_label.setObjectName("results-run-header")
        self.header_label.setWordWrap(True)
        layout.addWidget(self.header_label)

        self.primary_group = QGroupBox("Primary Plot", self)
        primary_layout = QVBoxLayout(self.primary_group)
        self.primary_plot = pg.PlotWidget(self.primary_group)
        self.primary_plot.setObjectName("results-primary-plot")
        self.primary_plot.setBackground("w")
        primary_layout.addWidget(self.primary_plot)
        layout.addWidget(self.primary_group, 1)

        self.secondary_group = QGroupBox("Secondary Plot", self)
        secondary_layout = QVBoxLayout(self.secondary_group)
        self.secondary_plot = pg.PlotWidget(self.secondary_group)
        self.secondary_plot.setObjectName("results-secondary-plot")
        self.secondary_plot.setBackground("w")
        secondary_layout.addWidget(self.secondary_plot)
        layout.addWidget(self.secondary_group, 1)

        self.summary_group = QGroupBox("Summary", self)
        summary_layout = QVBoxLayout(self.summary_group)
        self.summary_table = self._make_table(self.summary_group, "results-summary-table")
        summary_layout.addWidget(self.summary_table)
        layout.addWidget(self.summary_group)

        self.extra_summary_group = QGroupBox("Extra Summary", self)
        extra_summary_layout = QVBoxLayout(self.extra_summary_group)
        self.extra_summary_table = self._make_table(
            self.extra_summary_group,
            "results-extra-summary-table",
        )
        extra_summary_layout.addWidget(self.extra_summary_table)
        layout.addWidget(self.extra_summary_group)

    def _populate_plot(
        self,
        *,
        group: QGroupBox,
        plot: pg.PlotWidget,
        title: str,
        x_label: str,
        y_label: str,
        series: tuple[PlotSeries, ...],
    ) -> None:
        group.setTitle(title)
        self._clear_plot(plot)
        item = plot.getPlotItem()
        if item.legend is None:
            item.addLegend(offset=(10, 10))
        else:
            item.legend.clear()
        item.setTitle(title)
        item.setLabel("bottom", x_label)
        item.setLabel("left", y_label)
        for row in series:
            pen = pg.mkPen(
                row.color,
                width=2,
                style=Qt.PenStyle.DashLine if row.dashed else Qt.PenStyle.SolidLine,
            )
            item.plot(row.x_values, row.y_values, pen=pen, name=row.label)

    def _populate_summary_table(
        self,
        group: QGroupBox,
        table: QTableWidget,
        title: str,
        rows: tuple,
    ) -> None:
        if len(rows) == 0:
            group.hide()
            self._clear_table(table)
            return
        group.show()
        group.setTitle(title)
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            metric_item = QTableWidgetItem(row.label)
            value_item = QTableWidgetItem(row.value_text)
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

    def _clear_plot(self, plot: pg.PlotWidget) -> None:
        plot.clear()

    def _clear_table(self, table: QTableWidget) -> None:
        table.setRowCount(0)
        table.clearContents()

    @staticmethod
    def _finalize_item(item: QTableWidgetItem) -> None:
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)

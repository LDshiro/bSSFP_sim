"""Profile and time-series plots with cached items for fast playback updates."""

from __future__ import annotations

from contextlib import suppress

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from bssfpviz.gui.comparison_controller import ComparisonController, ResolvedSelection
from bssfpviz.gui.dataset_view_model import DatasetViewModel
from bssfpviz.gui.playback_controller import PlaybackController, PlaybackState

ACTIVE_PROFILE_COLOR = "#2a6fdb"
ACTIVE_SOS_COLOR = "#1c4f8a"
COMPARE_PROFILE_COLOR = "#f08c00"
COMPARE_SOS_COLOR = "#c92a2a"
ACTIVE_SERIES_COLORS = {"Mx": "#2a6fdb", "My": "#1b6ca8", "Mz": "#0f5132"}
COMPARE_SERIES_COLORS = {"Mx": "#f08c00", "My": "#ff922b", "Mz": "#c92a2a"}
ACTIVE_TRANSVERSE_SIGNAL_COLOR = "#087f5b"
COMPARE_TRANSVERSE_SIGNAL_COLOR = "#e67700"


class ProfilePanel(QWidget):
    """Display profile magnitude, selected-spin time series, and mean transverse signal."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm: DatasetViewModel | None = None
        self._controller: PlaybackController | ComparisonController | None = None
        self._last_curve_count = 0
        self._profile_marker_x = 0.0
        self._compare_marker_x: float | None = None
        self._time_marker_x = 0.0
        self._compare_time_marker_x: float | None = None
        self._profile_signature: tuple[object, ...] | None = None
        self._time_series_signature: tuple[object, ...] | None = None
        self._transverse_signal_signature: tuple[object, ...] | None = None
        self._profile_marker: pg.InfiniteLine | None = None
        self._compare_profile_marker: pg.InfiniteLine | None = None
        self._time_marker: pg.InfiniteLine | None = None
        self._compare_time_marker: pg.InfiniteLine | None = None
        self._transverse_signal_marker: pg.InfiniteLine | None = None
        self._compare_transverse_signal_marker: pg.InfiniteLine | None = None
        self._build_ui()
        self.clear()

    def clear(self) -> None:
        """Reset both plots to an empty state."""
        self._last_curve_count = 0
        self._profile_marker_x = 0.0
        self._compare_marker_x = None
        self._time_marker_x = 0.0
        self._compare_time_marker_x = None
        self._profile_signature = None
        self._time_series_signature = None
        self._transverse_signal_signature = None
        self._profile_marker = None
        self._compare_profile_marker = None
        self._time_marker = None
        self._compare_time_marker = None
        self._transverse_signal_marker = None
        self._compare_transverse_signal_marker = None
        self._reset_profile_plot()
        self._reset_time_series_plot()
        self._reset_transverse_signal_plot()

    def set_dataset(self, vm: DatasetViewModel | None) -> None:
        """Attach a single dataset view-model and redraw."""
        self._vm = vm
        if not isinstance(self._controller, ComparisonController):
            self.refresh_plots()

    def set_controller(
        self,
        controller: PlaybackController | ComparisonController | None,
    ) -> None:
        """Attach a controller and follow its state."""
        if self._controller is controller:
            self._render_from_current_controller()
            return

        self._disconnect_controller_signals()
        self._controller = controller
        self._connect_controller_signals(controller)
        self._render_from_current_controller()

    def refresh_plots(self) -> None:
        """Redraw the Chapter 6 single-dataset view."""
        if self._vm is None:
            self.clear()
            return
        state = self._state()
        self._plot_single_dataset(self._vm, state)

    def render_from_comparison_controller(self, controller: ComparisonController) -> None:
        """Render Chapter 7 profile/time-series overlays."""
        active_vm = controller.get_active_vm()
        active_selection = controller.resolve_active_selection()
        if active_vm is None or active_selection is None:
            self.clear()
            return
        if controller.get_other_vm() is None:
            self._plot_single_dataset(active_vm, controller.state())
            return

        other_vm = controller.get_other_vm()
        other_selection = controller.resolve_other_selection()
        self._plot_comparison(
            controller,
            active_vm,
            active_selection,
            other_vm,
            other_selection,
        )

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

    def _render_from_current_controller(self) -> None:
        if isinstance(self._controller, ComparisonController):
            self.render_from_comparison_controller(self._controller)
            return
        self.refresh_plots()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.profile_plot = pg.PlotWidget(self)
        self.profile_plot.setObjectName("profile-plot-widget")
        self.profile_plot.setBackground("w")
        self.plot_widget = self.profile_plot

        self.time_series_plot = pg.PlotWidget(self)
        self.time_series_plot.setObjectName("timeseries-plot-widget")
        self.time_series_plot.setBackground("w")
        self.time_series_widget = self.time_series_plot

        self.transverse_signal_plot = pg.PlotWidget(self)
        self.transverse_signal_plot.setObjectName("transverse-signal-plot-widget")
        self.transverse_signal_plot.setBackground("w")
        self.transverse_signal_widget = self.transverse_signal_plot

        layout.addWidget(self.profile_plot, 1)
        layout.addWidget(self.time_series_plot, 1)
        layout.addWidget(self.transverse_signal_plot, 1)

    def _reset_profile_plot(self) -> None:
        self.profile_plot.clear()
        item = self.profile_plot.getPlotItem()
        if item.legend is None:
            item.addLegend(offset=(10, 10))
        else:
            item.legend.clear()
        item.setTitle("Profiles")
        item.setLabel("bottom", "\u0394f [Hz]")
        item.setLabel("left", "Signal magnitude")

    def _reset_time_series_plot(self) -> None:
        self.time_series_plot.clear()
        item = self.time_series_plot.getPlotItem()
        if item.legend is None:
            item.addLegend(offset=(10, 10))
        else:
            item.legend.clear()
        item.setTitle("Selected Spin Time Series")
        item.setLabel("bottom", "t [s]")
        item.setLabel("left", "M")

    def _reset_transverse_signal_plot(self) -> None:
        self.transverse_signal_plot.clear()
        item = self.transverse_signal_plot.getPlotItem()
        if item.legend is None:
            item.addLegend(offset=(10, 10))
        else:
            item.legend.clear()
        item.setTitle("Mean Transverse Signal")
        item.setLabel("bottom", "t [s]")
        item.setLabel("left", "|mean(Mxy)|")

    def _plot_single_dataset(self, vm: DatasetViewModel, state: PlaybackState) -> None:
        profile_signature = ("single", id(vm))
        if self._profile_signature != profile_signature:
            self._reset_profile_plot()
            self._last_curve_count = 0
            profile_item = self.profile_plot.getPlotItem()
            for acquisition_index in range(vm.n_acq):
                magnitude = np.abs(vm.get_profile_complex(acquisition_index))
                profile_item.plot(
                    vm.delta_f_hz,
                    magnitude,
                    pen=pg.mkPen(ACTIVE_PROFILE_COLOR, width=2),
                    name=f"acq {acquisition_index}",
                )
                self._last_curve_count += 1

            profile_item.plot(
                vm.delta_f_hz,
                vm.get_sos_profile(),
                pen=pg.mkPen(ACTIVE_SOS_COLOR, width=3),
                name="SOS",
            )
            self._last_curve_count += 1
            self._profile_marker = _vertical_marker(0.0, dashed=False)
            profile_item.addItem(self._profile_marker)
            self._profile_signature = profile_signature

        time_series_signature = (
            "single",
            id(vm),
            state.mode,
            state.acquisition_index,
            state.spin_index,
        )
        if self._time_series_signature != time_series_signature:
            self._rebuild_time_series_plot(
                [
                    _SeriesSpec(
                        vm=vm,
                        mode=state.mode,
                        acquisition_index=state.acquisition_index,
                        spin_index=state.spin_index,
                        colors=ACTIVE_SERIES_COLORS,
                        dashed=False,
                    )
                ]
            )
            self._time_series_signature = time_series_signature

        transverse_signal_signature = (
            "single",
            id(vm),
            state.mode,
            state.acquisition_index,
        )
        if self._transverse_signal_signature != transverse_signal_signature:
            specs: list[_TransverseSignalSpec] = [
                _TransverseSignalSpec(
                    vm=vm,
                    mode=state.mode,
                    acquisition_index=state.acquisition_index,
                    color=ACTIVE_TRANSVERSE_SIGNAL_COLOR,
                    dashed=False,
                )
            ]
            self._rebuild_transverse_signal_plot(specs)
            self._transverse_signal_signature = transverse_signal_signature

        self._update_profile_marker(vm.get_selected_delta_f_hz(state.spin_index))
        self._update_time_marker(vm.get_current_time_s(state.mode, state.frame_index))

    def _plot_comparison(
        self,
        controller: ComparisonController,
        active_vm: DatasetViewModel,
        active_selection: ResolvedSelection,
        other_vm: DatasetViewModel | None,
        other_selection: ResolvedSelection | None,
    ) -> None:
        compare_enabled = (
            controller.session_state().compare_enabled
            and other_vm is not None
            and other_selection is not None
        )
        profile_signature = (
            "comparison",
            id(active_vm),
            active_selection.acquisition_index,
            id(other_vm) if compare_enabled and other_vm is not None else None,
            other_selection.acquisition_index if compare_enabled and other_selection else None,
            compare_enabled,
        )
        if self._profile_signature != profile_signature:
            self._reset_profile_plot()
            self._last_curve_count = 0
            profile_item = self.profile_plot.getPlotItem()

            active_profile = np.abs(
                active_vm.get_profile_complex(active_selection.acquisition_index)
            )
            profile_item.plot(
                active_vm.delta_f_hz,
                active_profile,
                pen=pg.mkPen(ACTIVE_PROFILE_COLOR, width=2),
                name=f"{active_selection.slot} acq {active_selection.acquisition_index}",
            )
            profile_item.plot(
                active_vm.delta_f_hz,
                active_vm.get_sos_profile(),
                pen=pg.mkPen(ACTIVE_SOS_COLOR, width=3),
                name=f"{active_selection.slot} SOS",
            )
            self._last_curve_count += 2

            if compare_enabled and other_vm is not None and other_selection is not None:
                compare_profile = np.abs(
                    other_vm.get_profile_complex(other_selection.acquisition_index)
                )
                profile_item.plot(
                    other_vm.delta_f_hz,
                    compare_profile,
                    pen=pg.mkPen(
                        COMPARE_PROFILE_COLOR,
                        width=2,
                        style=Qt.PenStyle.DashLine,
                    ),
                    name=f"{other_selection.slot} acq {other_selection.acquisition_index}",
                )
                profile_item.plot(
                    other_vm.delta_f_hz,
                    other_vm.get_sos_profile(),
                    pen=pg.mkPen(
                        COMPARE_SOS_COLOR,
                        width=2,
                        style=Qt.PenStyle.DashLine,
                    ),
                    name=f"{other_selection.slot} SOS",
                )
                self._last_curve_count += 2

            self._profile_marker = _vertical_marker(0.0, dashed=False)
            profile_item.addItem(self._profile_marker)
            if compare_enabled:
                self._compare_profile_marker = _vertical_marker(0.0, dashed=True)
                profile_item.addItem(self._compare_profile_marker)
            else:
                self._compare_profile_marker = None
            self._profile_signature = profile_signature

        time_series_signature = (
            "comparison",
            controller.session_state().mode,
            id(active_vm),
            active_selection.acquisition_index,
            active_selection.spin_index,
            id(other_vm) if compare_enabled and other_vm is not None else None,
            other_selection.acquisition_index if compare_enabled and other_selection else None,
            other_selection.spin_index if compare_enabled and other_selection else None,
        )
        if self._time_series_signature != time_series_signature:
            time_series_specs: list[_SeriesSpec] = [
                _SeriesSpec(
                    vm=active_vm,
                    mode=controller.session_state().mode,
                    acquisition_index=active_selection.acquisition_index,
                    spin_index=active_selection.spin_index,
                    colors=ACTIVE_SERIES_COLORS,
                    dashed=False,
                )
            ]
            if compare_enabled and other_vm is not None and other_selection is not None:
                time_series_specs.append(
                    _SeriesSpec(
                        vm=other_vm,
                        mode=controller.session_state().mode,
                        acquisition_index=other_selection.acquisition_index,
                        spin_index=other_selection.spin_index,
                        colors=COMPARE_SERIES_COLORS,
                        dashed=True,
                    )
                )
            self._rebuild_time_series_plot(time_series_specs)
            self._time_series_signature = time_series_signature

        transverse_signal_signature = (
            "comparison",
            controller.session_state().mode,
            id(active_vm),
            active_selection.acquisition_index,
            id(other_vm) if compare_enabled and other_vm is not None else None,
            other_selection.acquisition_index if compare_enabled and other_selection else None,
            compare_enabled,
        )
        if self._transverse_signal_signature != transverse_signal_signature:
            transverse_specs: list[_TransverseSignalSpec] = [
                _TransverseSignalSpec(
                    vm=active_vm,
                    mode=controller.session_state().mode,
                    acquisition_index=active_selection.acquisition_index,
                    color=ACTIVE_TRANSVERSE_SIGNAL_COLOR,
                    dashed=False,
                )
            ]
            if compare_enabled and other_vm is not None and other_selection is not None:
                transverse_specs.append(
                    _TransverseSignalSpec(
                        vm=other_vm,
                        mode=controller.session_state().mode,
                        acquisition_index=other_selection.acquisition_index,
                        color=COMPARE_TRANSVERSE_SIGNAL_COLOR,
                        dashed=True,
                    )
                )
            self._rebuild_transverse_signal_plot(transverse_specs)
            self._transverse_signal_signature = transverse_signal_signature

        self._update_profile_marker(active_selection.delta_f_hz)
        self._update_compare_profile_marker(
            None if not compare_enabled or other_selection is None else other_selection.delta_f_hz
        )
        self._update_time_marker(
            active_vm.get_current_time_s(
                controller.session_state().mode,
                active_selection.frame_index,
            )
        )
        self._update_compare_time_marker(
            None
            if not compare_enabled or other_vm is None or other_selection is None
            else other_vm.get_current_time_s(
                controller.session_state().mode,
                other_selection.frame_index,
            )
        )

    def _rebuild_time_series_plot(self, specs: list[_SeriesSpec]) -> None:
        self._reset_time_series_plot()
        time_item = self.time_series_plot.getPlotItem()
        for spec in specs:
            time_array = spec.vm.get_time_array_s(spec.mode)
            series = spec.vm.get_spin_series_xyz(
                spec.mode,
                spec.acquisition_index,
                spec.spin_index,
            )
            labels = ["Mx", "My", "Mz"]
            pen_style = Qt.PenStyle.DashLine if spec.dashed else Qt.PenStyle.SolidLine
            prefix = "cmp" if spec.dashed else "act"
            for axis_index, label in enumerate(labels):
                time_item.plot(
                    time_array,
                    series[:, axis_index],
                    pen=pg.mkPen(spec.colors[label], width=2, style=pen_style),
                    name=f"{prefix} {label}",
                )

        self._time_marker = _vertical_marker(0.0, dashed=False)
        time_item.addItem(self._time_marker)
        if any(spec.dashed for spec in specs):
            self._compare_time_marker = _vertical_marker(0.0, dashed=True)
            time_item.addItem(self._compare_time_marker)
        else:
            self._compare_time_marker = None

    def _rebuild_transverse_signal_plot(self, specs: list[_TransverseSignalSpec]) -> None:
        self._reset_transverse_signal_plot()
        item = self.transverse_signal_plot.getPlotItem()
        for spec in specs:
            time_array = spec.vm.get_time_array_s(spec.mode)
            transverse_signal = spec.vm.get_mean_transverse_magnitude_series(
                spec.mode,
                spec.acquisition_index,
            )
            prefix = "cmp" if spec.dashed else "act"
            item.plot(
                time_array,
                transverse_signal,
                pen=pg.mkPen(
                    spec.color,
                    width=2,
                    style=Qt.PenStyle.DashLine if spec.dashed else Qt.PenStyle.SolidLine,
                ),
                name=f"{prefix} |mean(Mxy)|",
            )

        self._transverse_signal_marker = _vertical_marker(0.0, dashed=False)
        item.addItem(self._transverse_signal_marker)
        if any(spec.dashed for spec in specs):
            self._compare_transverse_signal_marker = _vertical_marker(0.0, dashed=True)
            item.addItem(self._compare_transverse_signal_marker)
        else:
            self._compare_transverse_signal_marker = None

    def _update_profile_marker(self, x_value: float) -> None:
        self._profile_marker_x = float(x_value)
        if self._profile_marker is not None:
            self._profile_marker.setValue(self._profile_marker_x)

    def _update_compare_profile_marker(self, x_value: float | None) -> None:
        self._compare_marker_x = None if x_value is None else float(x_value)
        if self._compare_profile_marker is not None:
            self._compare_profile_marker.setVisible(x_value is not None)
            if x_value is not None:
                self._compare_profile_marker.setValue(self._compare_marker_x)

    def _update_time_marker(self, x_value: float) -> None:
        self._time_marker_x = float(x_value)
        if self._time_marker is not None:
            self._time_marker.setValue(self._time_marker_x)
        if self._transverse_signal_marker is not None:
            self._transverse_signal_marker.setValue(self._time_marker_x)

    def _update_compare_time_marker(self, x_value: float | None) -> None:
        self._compare_time_marker_x = None if x_value is None else float(x_value)
        if self._compare_time_marker is not None:
            self._compare_time_marker.setVisible(x_value is not None)
            if x_value is not None:
                self._compare_time_marker.setValue(self._compare_time_marker_x)
        if self._compare_transverse_signal_marker is not None:
            self._compare_transverse_signal_marker.setVisible(x_value is not None)
            if x_value is not None:
                self._compare_transverse_signal_marker.setValue(self._compare_time_marker_x)

    def _state(self) -> PlaybackState:
        if self._controller is not None:
            return self._controller.state()
        return PlaybackState(
            mode="reference",
            acquisition_index=0,
            spin_index=0,
            frame_index=0,
            is_playing=False,
            loop=True,
            fps=30.0,
        )

    def _handle_frame_changed(self, *_args: object) -> None:
        if isinstance(self._controller, ComparisonController):
            if self._controller.get_other_vm() is None:
                active_vm = self._controller.get_active_vm()
                if active_vm is None:
                    self.clear()
                    return
                state = self._controller.state()
                self._update_time_marker(
                    active_vm.get_current_time_s(state.mode, state.frame_index)
                )
                return
            active = self._controller.resolve_active_selection()
            if active is None:
                self.clear()
                return
            active_vm = self._controller.get_active_vm()
            if active_vm is None:
                self.clear()
                return
            self._update_time_marker(
                active_vm.get_current_time_s(
                    self._controller.session_state().mode,
                    active.frame_index,
                )
            )
            other_vm = self._controller.get_other_vm()
            other = self._controller.resolve_other_selection()
            self._update_compare_time_marker(
                None
                if other_vm is None or other is None
                else other_vm.get_current_time_s(
                    self._controller.session_state().mode, other.frame_index
                )
            )
            return

        state = self._state()
        if self._vm is not None:
            self._update_time_marker(self._vm.get_current_time_s(state.mode, state.frame_index))

    def _handle_structure_changed(self, *_args: object) -> None:
        self._render_from_current_controller()


class _SeriesSpec:
    def __init__(
        self,
        *,
        vm: DatasetViewModel,
        mode: str,
        acquisition_index: int,
        spin_index: int,
        colors: dict[str, str],
        dashed: bool,
    ) -> None:
        self.vm = vm
        self.mode = mode
        self.acquisition_index = acquisition_index
        self.spin_index = spin_index
        self.colors = colors
        self.dashed = dashed


class _TransverseSignalSpec:
    def __init__(
        self,
        *,
        vm: DatasetViewModel,
        mode: str,
        acquisition_index: int,
        color: str,
        dashed: bool,
    ) -> None:
        self.vm = vm
        self.mode = mode
        self.acquisition_index = acquisition_index
        self.color = color
        self.dashed = dashed


def _vertical_marker(x_value: float, *, dashed: bool) -> pg.InfiniteLine:
    marker = pg.InfiniteLine(pos=x_value, angle=90)
    marker.setPen(
        pg.mkPen(
            "#495057" if not dashed else "#868e96",
            width=1,
            style=Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine,
        )
    )
    return marker

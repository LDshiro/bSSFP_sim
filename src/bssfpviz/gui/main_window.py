"""Main Qt window for the Chapter 7 comparison GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
)

from bssfpviz.gui.adapters import (
    coerce_loaded_dataset_view,
    dataset_to_view_model,
    load_hdf5_dataset,
    make_default_run_config,
)
from bssfpviz.gui.bookmark_panel import BookmarkPanel
from bssfpviz.gui.comparison_controller import ComparisonController
from bssfpviz.gui.comparison_panel import ComparisonPanel
from bssfpviz.gui.compute_worker import ComputeWorker
from bssfpviz.gui.config_editor import ConfigEditor
from bssfpviz.gui.dataset_view_model import DatasetViewModel
from bssfpviz.gui.export_service import ExportService
from bssfpviz.gui.generic_preview_window import GenericPreviewWindow
from bssfpviz.gui.log_panel import LogPanel
from bssfpviz.gui.metadata_panel import MetadataPanel
from bssfpviz.gui.playback_bar import PlaybackBar
from bssfpviz.gui.profile_panel import ProfilePanel
from bssfpviz.gui.scene_panel import ScenePanel
from bssfpviz.io.session_json import load_session_json, save_session_json
from bssfpviz.models.config import AppConfig
from bssfpviz.models.results import SimulationDataset


class MainWindow(QMainWindow):
    """GUI shell for config editing, compute, playback, and two-dataset comparison."""

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self._app_config = config or AppConfig(
            window_title="Bloch / bSSFP Visualizer - Chapter 7",
            placeholder_text="Chapter 7 research comparison GUI",
            window_width=1520,
            window_height=980,
        )
        self._current_config_path: Path | None = None
        self._current_dataset_path: Path | None = None
        self._current_dataset: Any | None = None
        self._current_view_model: DatasetViewModel | None = None
        self._primary_dataset_path: Path | None = None
        self._compare_dataset_path: Path | None = None
        self._primary_dataset: Any | None = None
        self._compare_dataset: Any | None = None
        self._primary_view_model: DatasetViewModel | None = None
        self._compare_view_model: DatasetViewModel | None = None
        self._compute_thread: QThread | None = None
        self._compute_worker: ComputeWorker | None = None
        self._generic_preview_window: GenericPreviewWindow | None = None
        self._is_running = False

        self.comparison_controller = ComparisonController(self)
        self.playback_controller = self.comparison_controller
        self.export_service = ExportService()

        self.setWindowTitle(self._app_config.window_title)
        self.resize(self._app_config.window_width, self._app_config.window_height)
        self._build_ui()
        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._connect_actions()
        self.on_new_config()

    def on_new_config(self) -> None:
        """Reset the config editor to the default GUI config."""
        self.config_editor.set_config(make_default_run_config())
        self._current_config_path = None
        self._set_status_message("New config")
        self.log_panel.append_log("new config created")

    def on_load_config(self) -> None:
        """Load a YAML compute config from disk."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load Config",
            "examples/configs",
            "YAML Files (*.yaml *.yml)",
        )
        if not file_name:
            return

        path = Path(file_name)
        try:
            self.config_editor.load_yaml(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Load Config Failed", str(exc))
            self.log_panel.append_log(f"config load failed: {path}")
            return

        self._current_config_path = path
        self._set_status_message("Config loaded")
        self.log_panel.append_log(f"config loaded: {path}")

    def on_save_config_as(self) -> None:
        """Save the current config editor contents as YAML."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Config As",
            "examples/configs/chapter5_default.yaml",
            "YAML Files (*.yaml *.yml)",
        )
        if not file_name:
            return

        path = Path(file_name)
        try:
            self.config_editor.save_yaml(path)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Config", str(exc))
            self.log_panel.append_log(f"config save failed: {exc}")
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save Config Failed", str(exc))
            self.log_panel.append_log(f"config save failed: {exc}")
            return

        self._current_config_path = path
        self._set_status_message("Config saved")
        self.log_panel.append_log(f"config saved: {path}")

    def on_open_hdf5(self) -> None:
        """Compatibility alias that opens a primary dataset."""
        self.on_open_primary_dataset()

    def on_open_primary_dataset(self) -> None:
        """Open an existing primary HDF5 dataset file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Primary Dataset",
            "data/generated",
            "HDF5 Files (*.h5 *.hdf5)",
        )
        if file_name:
            self.load_dataset_from_path(Path(file_name), slot="primary")

    def on_open_compare_dataset(self) -> None:
        """Open an existing compare HDF5 dataset file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Compare Dataset",
            "data/generated",
            "HDF5 Files (*.h5 *.hdf5)",
        )
        if file_name:
            self.load_dataset_from_path(Path(file_name), slot="compare")

    def on_save_session_preset(self) -> None:
        """Persist the current comparison/playback state as JSON."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Session Preset",
            "data/generated/chapter7_session.json",
            "JSON Files (*.json)",
        )
        if not file_name:
            return

        path = Path(file_name)
        try:
            save_session_json(path, self.comparison_controller.session_state())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save Session Failed", str(exc))
            self.log_panel.append_log(f"session save failed: {exc}")
            return

        self._set_status_message("Session preset saved")
        self.log_panel.append_log(f"session saved: {path}")

    def on_load_session_preset(self) -> None:
        """Restore comparison/playback state from a saved session preset."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session Preset",
            "data/generated",
            "JSON Files (*.json)",
        )
        if not file_name:
            return

        path = Path(file_name)
        try:
            session = load_session_json(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Load Session Failed", str(exc))
            self.log_panel.append_log(f"session load failed: {exc}")
            return

        missing_paths: list[str] = []
        if session.primary_path is None:
            self._clear_dataset_slot("primary")
        if session.compare_path is None:
            self._clear_dataset_slot("compare")
        if session.primary_path:
            primary_path = Path(session.primary_path)
            if primary_path.exists():
                self.load_dataset_from_path(primary_path, slot="primary", make_active=False)
            else:
                self._clear_dataset_slot("primary")
                missing_paths.append(session.primary_path)
        if session.compare_path:
            compare_path = Path(session.compare_path)
            if compare_path.exists():
                self.load_dataset_from_path(compare_path, slot="compare", make_active=False)
            else:
                self._clear_dataset_slot("compare")
                missing_paths.append(session.compare_path)

        self.comparison_controller.set_session_state(session)
        self._sync_active_dataset_aliases()
        self._refresh_metadata_panel()
        self._update_status_from_controller("Session preset loaded")
        self.log_panel.append_log(f"session loaded: {path}")

        if missing_paths:
            QMessageBox.warning(
                self,
                "Missing Dataset Paths",
                "Some datasets from the session preset were not found:\n"
                + "\n".join(missing_paths),
            )

    def on_export_current_view_bundle(self) -> None:
        """Export screenshots and session state for the current GUI view."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Export Current View Bundle",
            "data/generated",
        )
        if not directory:
            return

        output_dir = Path(directory)
        try:
            self.export_service.export_current_view_bundle(
                output_dir=output_dir,
                main_window=self,
                scene_panel=self.scene_panel,
                profile_panel=self.profile_panel,
                time_series_widget=self.profile_panel.time_series_widget,
                session_state=self.comparison_controller.session_state(),
                notes={
                    "primary_path": str(self._primary_dataset_path or ""),
                    "compare_path": str(self._compare_dataset_path or ""),
                },
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Failed", str(exc))
            self.log_panel.append_log(f"export failed: {exc}")
            return

        self._set_status_message("Export bundle created")
        self.log_panel.append_log(f"exported bundle: {output_dir}")

    def on_open_generic_preview(self) -> None:
        """Open the preview-only generic inspector shell."""
        if self._generic_preview_window is None:
            self._generic_preview_window = GenericPreviewWindow(self)
            self._generic_preview_window.destroyed.connect(self._clear_generic_preview_window)
        self._generic_preview_window.show()
        self._generic_preview_window.raise_()
        self._generic_preview_window.activateWindow()

    def on_run_compute(self) -> None:
        """Start a background compute run from the current config."""
        if self._is_running:
            return

        try:
            config = self.config_editor.get_config()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Config", str(exc))
            self.log_panel.append_log(f"config validation failed: {exc}")
            return

        default_output = Path("data/generated") / f"{config.meta.case_name}.h5"
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Run Compute",
            str(default_output),
            "HDF5 Files (*.h5 *.hdf5)",
        )
        if not file_name:
            return

        output_path = Path(file_name)
        self._set_running_state(True, message="Running...")
        self._start_compute_worker(config, output_path)

    def on_compute_finished(self, summary: object, output_path: object) -> None:
        """Handle a successful compute run and auto-load the saved result."""
        case_name = getattr(summary, "case_name", "compute")
        resolved_path = output_path if isinstance(output_path, Path) else Path(str(output_path))
        try:
            self.load_dataset_from_path(resolved_path, slot="primary")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Load Result Failed", str(exc))
            self.log_panel.append_log(f"dataset auto-load failed: {exc}")
        finally:
            self._set_running_state(False, message=f"Finished: {case_name}")

    def on_compute_failed(self, message: str, tb: str) -> None:
        """Handle background compute failures."""
        self._set_running_state(False, message="Compute failed")
        self.log_panel.append_log(tb)
        QMessageBox.critical(self, "Compute Failed", message)

    def load_dataset_from_path(
        self,
        path: Path,
        slot: str = "primary",
        *,
        make_active: bool | None = None,
    ) -> None:
        """Load a dataset from disk into the requested slot."""
        dataset = load_hdf5_dataset(path)
        activate = (slot == "primary") if make_active is None else make_active
        self._apply_loaded_dataset(dataset, slot=slot, path=path, make_active=activate)
        self.log_panel.append_log(f"{slot} dataset loaded: {path}")

    def refresh_views_from_dataset(self, dataset: Any, path: Path | None = None) -> None:
        """Compatibility helper that replaces the primary dataset."""
        self._apply_loaded_dataset(dataset, slot="primary", path=path, make_active=True)

    def set_loaded_dataset(self, dataset: SimulationDataset) -> None:
        """Attach an in-memory canonical dataset as the primary slot."""
        self.refresh_views_from_dataset(dataset, self._current_dataset_path)

    def set_compare_dataset(self, dataset: SimulationDataset) -> None:
        """Attach an in-memory canonical dataset as the compare slot."""
        self._apply_loaded_dataset(
            dataset,
            slot="compare",
            path=self._compare_dataset_path,
            make_active=False,
        )

    def set_loaded_dataset_slot(self, dataset: Any, *, slot: str, path: Path | None = None) -> None:
        """Attach an in-memory dataset to a specific comparison slot."""
        self._apply_loaded_dataset(dataset, slot=slot, path=path, make_active=(slot == "primary"))

    def _build_ui(self) -> None:
        self.config_editor = ConfigEditor(self)
        self.scene_panel = ScenePanel(self)
        self.profile_panel = ProfilePanel(self)
        self.time_series_panel = self.profile_panel
        self.metadata_panel = MetadataPanel(self)
        self.log_panel = LogPanel(self)
        self.comparison_panel = ComparisonPanel(self)
        self.bookmark_panel = BookmarkPanel(self)
        self.playback_bar = PlaybackBar(self)

        self.scene_panel.set_controller(self.comparison_controller)
        self.profile_panel.set_controller(self.comparison_controller)
        self.playback_bar.set_controller(self.comparison_controller)
        self.comparison_panel.set_controller(self.comparison_controller)
        self.bookmark_panel.set_controller(self.comparison_controller)

        tab_widget = QTabWidget(self)
        tab_widget.addTab(self.profile_panel, "Profile")
        tab_widget.addTab(self.metadata_panel, "Metadata")
        tab_widget.addTab(self.log_panel, "Log")

        upper_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        upper_splitter.addWidget(self.scene_panel)
        upper_splitter.addWidget(tab_widget)
        upper_splitter.setStretchFactor(0, 2)
        upper_splitter.setStretchFactor(1, 1)

        comparison_widget = QWidget(self)
        comparison_layout = QHBoxLayout(comparison_widget)
        comparison_layout.setContentsMargins(0, 0, 0, 0)
        comparison_layout.addWidget(self.comparison_panel, 2)
        comparison_layout.addWidget(self.bookmark_panel, 1)

        right_splitter = QSplitter(Qt.Orientation.Vertical, self)
        right_splitter.addWidget(upper_splitter)
        right_splitter.addWidget(comparison_widget)
        right_splitter.addWidget(self.playback_bar)
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 0)
        right_splitter.setStretchFactor(2, 0)

        root_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        root_splitter.addWidget(self.config_editor)
        root_splitter.addWidget(right_splitter)
        root_splitter.setStretchFactor(0, 0)
        root_splitter.setStretchFactor(1, 1)
        self.setCentralWidget(root_splitter)

        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        self.loaded_file_label = QLabel("File: -", self)
        self.loaded_file_label.setObjectName("status-loaded-file")
        self.run_state_label = QLabel("Idle", self)
        self.run_state_label.setObjectName("status-run-state")
        self.summary_message_label = QLabel("Ready", self)
        self.summary_message_label.setObjectName("status-summary-message")
        status_bar.addWidget(self.loaded_file_label, 1)
        status_bar.addPermanentWidget(self.run_state_label)
        status_bar.addPermanentWidget(self.summary_message_label, 1)

    def _create_actions(self) -> None:
        self.new_config_action = QAction("New Config", self)
        self.load_config_action = QAction("Load Config...", self)
        self.save_config_action = QAction("Save Config As...", self)
        self.open_hdf5_action = QAction("Open Primary Dataset...", self)
        self.open_primary_dataset_action = self.open_hdf5_action
        self.open_compare_dataset_action = QAction("Open Compare Dataset...", self)
        self.open_generic_preview_action = QAction("Open Generic Preview...", self)
        self.save_session_action = QAction("Save Session Preset...", self)
        self.load_session_action = QAction("Load Session Preset...", self)
        self.export_bundle_action = QAction("Export Current View Bundle...", self)
        self.quit_action = QAction("Quit", self)
        self.run_compute_action = QAction("Run Compute...", self)
        self.reset_view_action = QAction("Reset 3D View", self)
        self.clear_log_action = QAction("Clear Log", self)
        self.play_pause_action = QAction("Play / Pause", self)
        self.step_forward_action = QAction("Step Forward", self)
        self.step_backward_action = QAction("Step Backward", self)
        self.about_action = QAction("About", self)

        self.new_config_action.setObjectName("action-new-config")
        self.load_config_action.setObjectName("action-load-config")
        self.save_config_action.setObjectName("action-save-config")
        self.open_hdf5_action.setObjectName("action-open-hdf5")
        self.open_compare_dataset_action.setObjectName("action-open-compare-dataset")
        self.open_generic_preview_action.setObjectName("action-open-generic-preview")
        self.save_session_action.setObjectName("action-save-session")
        self.load_session_action.setObjectName("action-load-session")
        self.export_bundle_action.setObjectName("action-export-bundle")
        self.run_compute_action.setObjectName("action-run-compute")
        self.play_pause_action.setObjectName("action-play-pause")
        self.step_forward_action.setObjectName("action-step-forward")
        self.step_backward_action.setObjectName("action-step-backward")

    def _create_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.new_config_action)
        file_menu.addAction(self.load_config_action)
        file_menu.addAction(self.save_config_action)
        file_menu.addSeparator()
        file_menu.addAction(self.open_primary_dataset_action)
        file_menu.addAction(self.open_compare_dataset_action)
        file_menu.addAction(self.open_generic_preview_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_session_action)
        file_menu.addAction(self.load_session_action)
        file_menu.addAction(self.export_bundle_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        run_menu = self.menuBar().addMenu("Run")
        run_menu.addAction(self.run_compute_action)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(self.play_pause_action)
        view_menu.addAction(self.step_backward_action)
        view_menu.addAction(self.step_forward_action)
        view_menu.addSeparator()
        view_menu.addAction(self.reset_view_action)
        view_menu.addAction(self.clear_log_action)

        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction(self.about_action)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setObjectName("main-toolbar")
        toolbar.addAction(self.new_config_action)
        toolbar.addAction(self.load_config_action)
        toolbar.addAction(self.save_config_action)
        toolbar.addAction(self.open_primary_dataset_action)
        toolbar.addAction(self.open_compare_dataset_action)
        toolbar.addAction(self.open_generic_preview_action)
        toolbar.addSeparator()
        toolbar.addAction(self.save_session_action)
        toolbar.addAction(self.load_session_action)
        toolbar.addAction(self.export_bundle_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_compute_action)
        toolbar.addSeparator()
        toolbar.addAction(self.play_pause_action)
        toolbar.addAction(self.step_backward_action)
        toolbar.addAction(self.step_forward_action)
        toolbar.addAction(self.reset_view_action)
        toolbar.addAction(self.clear_log_action)
        self.addToolBar(toolbar)

    def _connect_actions(self) -> None:
        self.new_config_action.triggered.connect(self.on_new_config)
        self.load_config_action.triggered.connect(self.on_load_config)
        self.save_config_action.triggered.connect(self.on_save_config_as)
        self.open_primary_dataset_action.triggered.connect(self.on_open_primary_dataset)
        self.open_compare_dataset_action.triggered.connect(self.on_open_compare_dataset)
        self.open_generic_preview_action.triggered.connect(self.on_open_generic_preview)
        self.save_session_action.triggered.connect(self.on_save_session_preset)
        self.load_session_action.triggered.connect(self.on_load_session_preset)
        self.export_bundle_action.triggered.connect(self.on_export_current_view_bundle)
        self.quit_action.triggered.connect(self.close)
        self.run_compute_action.triggered.connect(self.on_run_compute)
        self.reset_view_action.triggered.connect(self.scene_panel.reset_camera)
        self.clear_log_action.triggered.connect(self.log_panel.clear_log)
        self.play_pause_action.triggered.connect(self.comparison_controller.toggle_play)
        self.step_forward_action.triggered.connect(self.comparison_controller.step_forward)
        self.step_backward_action.triggered.connect(self.comparison_controller.step_backward)
        self.about_action.triggered.connect(self._show_about_dialog)
        self.config_editor.run_button.clicked.connect(self.on_run_compute)

        self.comparison_controller.selection_changed.connect(self._on_controller_selection_changed)
        self.comparison_controller.datasets_changed.connect(self._on_datasets_changed)
        self.comparison_controller.bookmarks_changed.connect(self.bookmark_panel.refresh)

    def _apply_loaded_dataset(
        self,
        dataset: Any,
        *,
        slot: str,
        path: Path | None,
        make_active: bool = True,
    ) -> None:
        view = coerce_loaded_dataset_view(dataset, path=path)
        vm = dataset_to_view_model(view)
        resolved_path = path or view.source_path
        path_text = None if resolved_path is None else str(resolved_path)

        if slot == "primary":
            self._primary_dataset = view
            self._primary_dataset_path = resolved_path
            self._primary_view_model = vm
            self.comparison_controller.set_primary_dataset(vm, path_text)
            if make_active or self._compare_view_model is None:
                self.comparison_controller.set_active_slot("primary")
        elif slot == "compare":
            self._compare_dataset = view
            self._compare_dataset_path = resolved_path
            self._compare_view_model = vm
            self.comparison_controller.set_compare_dataset(vm, path_text)
            self.comparison_controller.set_compare_enabled(vm is not None)
            if make_active:
                self.comparison_controller.set_active_slot("compare")
        else:
            msg = f"Unsupported dataset slot: {slot!r}"
            raise ValueError(msg)

        self._sync_active_dataset_aliases()
        self._refresh_metadata_panel()
        self._update_status_from_controller("Dataset loaded")

    def _clear_dataset_slot(self, slot: str) -> None:
        if slot == "primary":
            self._primary_dataset = None
            self._primary_dataset_path = None
            self._primary_view_model = None
            self.comparison_controller.set_primary_dataset(None, None)
        elif slot == "compare":
            self._compare_dataset = None
            self._compare_dataset_path = None
            self._compare_view_model = None
            self.comparison_controller.set_compare_dataset(None, None)
            self.comparison_controller.set_compare_enabled(False)
        else:
            msg = f"Unsupported dataset slot: {slot!r}"
            raise ValueError(msg)
        self._sync_active_dataset_aliases()
        self._refresh_metadata_panel()
        self._update_status_from_controller()

    def _start_compute_worker(self, config: Any, output_path: Path) -> None:
        thread = QThread(self)
        worker = ComputeWorker(config, output_path)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self.on_compute_finished)
        worker.failed.connect(self.on_compute_failed)
        worker.log.connect(self.log_panel.append_log)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_compute_thread)

        self._compute_thread = thread
        self._compute_worker = worker
        thread.start()

    def _clear_compute_thread(self) -> None:
        self._compute_thread = None
        self._compute_worker = None

    def _clear_generic_preview_window(self) -> None:
        self._generic_preview_window = None

    def _set_running_state(self, running: bool, *, message: str) -> None:
        self._is_running = running
        self.run_compute_action.setEnabled(not running)
        self.config_editor.run_button.setEnabled(not running)
        self.run_state_label.setText("Running" if running else "Idle")
        self.summary_message_label.setText(message)

    def _set_loaded_file(self, path: Path | None) -> None:
        self.loaded_file_label.setText(f"File: {path}" if path is not None else "File: -")

    def _set_status_message(self, message: str) -> None:
        self.summary_message_label.setText(message)

    def _show_about_dialog(self) -> None:
        QMessageBox.information(
            self,
            "About",
            "Bloch / bSSFP Visualizer - Chapter 7\n"
            "Comparison GUI with session presets, bookmarks, and screenshot bundles.",
        )

    def _sync_active_dataset_aliases(self) -> None:
        active_slot = self.comparison_controller.session_state().active_slot
        previous_view_model = self._current_view_model
        if active_slot == "compare" and self._compare_view_model is not None:
            self._current_dataset = self._compare_dataset
            self._current_dataset_path = self._compare_dataset_path
            self._current_view_model = self._compare_view_model
        else:
            self._current_dataset = self._primary_dataset
            self._current_dataset_path = self._primary_dataset_path
            self._current_view_model = self._primary_view_model

        if self._current_view_model is not previous_view_model:
            self.scene_panel.set_dataset(self._current_view_model)
            self.profile_panel.set_dataset(self._current_view_model)

    def _refresh_metadata_panel(self) -> None:
        self.metadata_panel.set_comparison_state(
            primary_dataset=self._primary_dataset,
            primary_path=self._primary_dataset_path,
            compare_dataset=self._compare_dataset,
            compare_path=self._compare_dataset_path,
            active_slot=self.comparison_controller.session_state().active_slot,
            compare_enabled=self.comparison_controller.session_state().compare_enabled,
        )

    def _on_controller_selection_changed(self) -> None:
        self._sync_active_dataset_aliases()
        self._refresh_metadata_panel()
        self._update_status_from_controller()

    def _on_datasets_changed(self) -> None:
        self._sync_active_dataset_aliases()
        self._refresh_metadata_panel()
        self._update_status_from_controller()

    def _update_status_from_controller(self, message: str | None = None) -> None:
        active_slot = self.comparison_controller.session_state().active_slot
        active_path = (
            self._compare_dataset_path if active_slot == "compare" else self._primary_dataset_path
        )
        self._set_loaded_file(active_path)
        if message is not None:
            self._set_status_message(message)

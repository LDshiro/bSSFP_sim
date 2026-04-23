"""Generic preview shell for timing and contrast inspection."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bssfpviz.gui.bundle_metadata_panel import BundleMetadataPanel
from bssfpviz.gui.bundle_view_models import (
    build_bundle_metadata_view_model,
    build_comparison_summary_view_model,
    build_results_comparison_view_model,
)
from bssfpviz.gui.compare_worker import CompareWorker
from bssfpviz.gui.comparison_summary_panel import ComparisonSummaryPanel
from bssfpviz.gui.experiment_editor import ExperimentEditor
from bssfpviz.gui.generic_scene_panel import GenericScenePanel
from bssfpviz.gui.log_panel import LogPanel
from bssfpviz.gui.preview_view_models import (
    build_sequence_comparison_view_model,
    build_timing_contrast_comparison_view_model,
)
from bssfpviz.gui.results_panel import ResultsPanel
from bssfpviz.gui.sequence_panel import SequencePanel
from bssfpviz.gui.timing_contrast_panel import TimingContrastPanel
from bssfpviz.io.comparison_hdf5 import (
    load_comparison_bundle,
    read_comparison_bundle_file_info,
)
from bssfpviz.models.comparison import ComparisonBundle, ExperimentConfig
from bssfpviz.workflows.preview import ExperimentPreviewSummary, build_experiment_preview


class GenericPreviewWindow(QWidget):
    """Generic viewer shell for preview and bundle-driven comparison inspection."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_config_path: Path | None = None
        self._current_preview_summary: ExperimentPreviewSummary | None = None
        self._current_bundle_path: Path | None = None
        self._current_bundle: ComparisonBundle | None = None
        self._current_bundle_file_info: dict[str, str] = {}
        self._last_bundle_warning_signature: tuple[str, ...] = ()
        self._compare_thread: QThread | None = None
        self._compare_worker: CompareWorker | None = None
        self.setWindowTitle("Generic Sequence Preview")
        self.resize(1320, 860)
        self._build_ui()

    def load_config_from_path(self, path: Path) -> None:
        """Load one experiment YAML and refresh the preview inspector."""
        config = self.experiment_editor.load_yaml(path)
        self._refresh_preview_from_config(config, path)

    def load_bundle_from_path(self, path: Path) -> None:
        """Load one comparison bundle and refresh bundle-driven inspectors."""
        bundle = load_comparison_bundle(path)
        file_info = read_comparison_bundle_file_info(path)
        self._apply_bundle(bundle, path, file_info)

    def refresh_preview(self) -> None:
        """Refresh preview from the current structured editor state."""
        config = self.experiment_editor.get_config()
        config_path = self._current_config_path or Path("<editor>")
        self._refresh_preview_from_config(config, config_path)

    def clear_bundle(self) -> None:
        """Clear the currently loaded comparison bundle."""
        self._current_bundle = None
        self._current_bundle_path = None
        self._current_bundle_file_info = {}
        self._last_bundle_warning_signature = ()
        self.bundle_path_edit.clear()
        self.last_bundle_loaded_label.setText("Last bundle load: -")
        self.results_panel.clear()
        self.comparison_summary_panel.clear()
        self.bundle_metadata_panel.clear()
        self.scene_panel.clear()
        self._append_log("Cleared comparison bundle.")
        self.status_label.setText("Status: bundle cleared")

    def on_load_yaml(self) -> None:
        """Open a file dialog and load an experiment YAML file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Experiment YAML",
            "examples/configs",
            "YAML Files (*.yaml *.yml)",
        )
        if not file_name:
            return
        try:
            self.load_config_from_path(Path(file_name))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Load Preview Failed", str(exc))
            self.status_label.setText(f"Load failed: {exc}")
            self._append_log(f"Preview load failed: {exc}")

    def on_refresh_preview(self) -> None:
        """Refresh the preview from the currently loaded YAML file."""
        try:
            self.refresh_preview()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Refresh Preview Failed", str(exc))
            self.status_label.setText(f"Refresh failed: {exc}")
            self._append_log(f"Preview refresh failed: {exc}")

    def on_save_yaml(self) -> None:
        """Save the current editor state to a YAML file."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Experiment YAML",
            "examples/configs/generic_experiment.yaml",
            "YAML Files (*.yaml *.yml)",
        )
        if not file_name:
            return
        try:
            path = Path(file_name)
            self.experiment_editor.save_yaml(path)
            self._current_config_path = path
            self.config_path_edit.setText(str(path))
            self.status_label.setText(f"Status: YAML saved to {path.name}")
            self._append_log(f"Saved experiment YAML: {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save YAML Failed", str(exc))
            self.status_label.setText(f"Save failed: {exc}")
            self._append_log(f"YAML save failed: {exc}")

    def on_load_bundle(self) -> None:
        """Open a file dialog and load a comparison HDF5 bundle."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Comparison Bundle",
            "data/generated",
            "HDF5 Files (*.h5 *.hdf5)",
        )
        if not file_name:
            return
        try:
            self.load_bundle_from_path(Path(file_name))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Load Bundle Failed", str(exc))
            self.status_label.setText(f"Bundle load failed: {exc}")
            self._append_log(f"Bundle load failed: {exc}")

    def on_clear_bundle(self) -> None:
        """Clear the active comparison bundle."""
        self.clear_bundle()

    def on_run_compare(self) -> None:
        """Ask for an output path and run comparison in the background."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Comparison Bundle",
            "data/generated/generic_comparison.h5",
            "HDF5 Files (*.h5 *.hdf5)",
        )
        if not file_name:
            return
        output_path = Path(file_name)
        overwrite = False
        if output_path.exists():
            answer = QMessageBox.question(
                self,
                "Overwrite Bundle?",
                f"Overwrite existing bundle?\n{output_path}",
            )
            overwrite = answer == QMessageBox.StandardButton.Yes
        try:
            self.run_compare_to_path(output_path, overwrite=overwrite)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Run Compare Failed", str(exc))
            self.status_label.setText(f"Compare failed: {exc}")
            self._append_log(f"Compare launch failed: {exc}")

    def run_compare_to_path(self, path: Path, *, overwrite: bool = False) -> None:
        """Run comparison from the current editor state and auto-load the output bundle."""
        if self._compare_thread is not None:
            msg = "A comparison run is already in progress."
            raise RuntimeError(msg)
        if path.exists() and not overwrite:
            msg = f"Output file already exists: {path}"
            raise FileExistsError(msg)
        config = self.experiment_editor.get_config()
        self._start_compare_worker(config, path)

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)

        splitter = QSplitter(self)
        root_layout.addWidget(splitter)

        source_panel = QWidget(splitter)
        source_layout = QVBoxLayout(source_panel)
        preview_group = QGroupBox("Experiment YAML", source_panel)
        preview_group.setObjectName("generic-preview-source-group")
        preview_group_layout = QVBoxLayout(preview_group)

        self.config_path_edit = QLineEdit(preview_group)
        self.config_path_edit.setObjectName("generic-preview-config-path")
        self.config_path_edit.setReadOnly(True)
        self.config_path_edit.setPlaceholderText("Load an Experiment YAML...")
        self.load_yaml_button = QPushButton("Load YAML...", preview_group)
        self.load_yaml_button.setObjectName("generic-preview-load-button")
        self.save_yaml_button = QPushButton("Save YAML...", preview_group)
        self.save_yaml_button.setObjectName("generic-preview-save-button")
        self.refresh_button = QPushButton("Refresh Preview", preview_group)
        self.refresh_button.setObjectName("generic-preview-refresh-button")
        self.last_refreshed_label = QLabel("Last refreshed: -", preview_group)
        self.last_refreshed_label.setObjectName("generic-preview-last-refreshed")
        self.experiment_editor = ExperimentEditor(preview_group)
        self.experiment_editor.setObjectName("generic-experiment-editor")
        preview_group_layout.addWidget(QLabel("config path", preview_group))
        preview_group_layout.addWidget(self.config_path_edit)
        preview_group_layout.addWidget(self.load_yaml_button)
        preview_group_layout.addWidget(self.save_yaml_button)
        preview_group_layout.addWidget(self.refresh_button)
        preview_group_layout.addWidget(self.last_refreshed_label)
        preview_group_layout.addWidget(self.experiment_editor, 1)

        bundle_group = QGroupBox("Comparison Bundle", source_panel)
        bundle_group.setObjectName("generic-preview-bundle-group")
        bundle_group_layout = QVBoxLayout(bundle_group)
        self.bundle_path_edit = QLineEdit(bundle_group)
        self.bundle_path_edit.setObjectName("generic-preview-bundle-path")
        self.bundle_path_edit.setReadOnly(True)
        self.bundle_path_edit.setPlaceholderText("Load a comparison bundle...")
        self.load_bundle_button = QPushButton("Load Bundle...", bundle_group)
        self.load_bundle_button.setObjectName("generic-preview-load-bundle-button")
        self.clear_bundle_button = QPushButton("Clear Bundle", bundle_group)
        self.clear_bundle_button.setObjectName("generic-preview-clear-bundle-button")
        self.run_compare_button = QPushButton("Run Compare...", bundle_group)
        self.run_compare_button.setObjectName("generic-preview-run-compare-button")
        self.last_bundle_loaded_label = QLabel("Last bundle load: -", bundle_group)
        self.last_bundle_loaded_label.setObjectName("generic-preview-last-bundle-load")
        bundle_group_layout.addWidget(QLabel("bundle path", bundle_group))
        bundle_group_layout.addWidget(self.bundle_path_edit)
        bundle_group_layout.addWidget(self.run_compare_button)
        bundle_group_layout.addWidget(self.load_bundle_button)
        bundle_group_layout.addWidget(self.clear_bundle_button)
        bundle_group_layout.addWidget(self.last_bundle_loaded_label)
        bundle_group_layout.addStretch(1)

        self.status_label = QLabel("Status: idle", source_panel)
        self.status_label.setObjectName("generic-preview-status")
        self.status_label.setWordWrap(True)

        source_layout.addWidget(preview_group)
        source_layout.addWidget(bundle_group)
        source_layout.addWidget(self.status_label)
        source_layout.addStretch(1)

        inspector_panel = QWidget(splitter)
        inspector_layout = QVBoxLayout(inspector_panel)
        self.inspector_tabs = QTabWidget(inspector_panel)
        self.inspector_tabs.setObjectName("generic-preview-tabs")
        self.sequence_panel = SequencePanel(self.inspector_tabs)
        self.inspector_tabs.addTab(self.sequence_panel, "Sequence")
        self.timing_contrast_panel = TimingContrastPanel(self.inspector_tabs)
        self.inspector_tabs.addTab(self.timing_contrast_panel, "Timing / Contrast")
        self.scene_panel = GenericScenePanel(self.inspector_tabs)
        self.inspector_tabs.addTab(self.scene_panel, "Scene")
        self.results_panel = ResultsPanel(self.inspector_tabs)
        self.inspector_tabs.addTab(self.results_panel, "Results")
        self.comparison_summary_panel = ComparisonSummaryPanel(self.inspector_tabs)
        self.inspector_tabs.addTab(self.comparison_summary_panel, "Comparison")
        self.bundle_metadata_panel = BundleMetadataPanel(self.inspector_tabs)
        self.inspector_tabs.addTab(self.bundle_metadata_panel, "Metadata")
        self.log_panel = LogPanel(self.inspector_tabs)
        self.inspector_tabs.addTab(self.log_panel, "Log")
        notes_widget = QWidget(self.inspector_tabs)
        notes_layout = QVBoxLayout(notes_widget)
        notes_label = QLabel(
            "Sequence and Timing / Contrast use the loaded Experiment YAML preview.\n"
            "Scene, Results, Comparison, and Metadata use the loaded comparison bundle.\n"
            "Run Compare executes the same backend as bssfpviz-compare and auto-loads the bundle.",
            notes_widget,
        )
        notes_label.setObjectName("generic-preview-notes")
        notes_label.setWordWrap(True)
        notes_layout.addWidget(notes_label)
        notes_layout.addStretch(1)
        self.inspector_tabs.addTab(notes_widget, "Inspector Notes")
        inspector_layout.addWidget(self.inspector_tabs)

        splitter.addWidget(source_panel)
        splitter.addWidget(inspector_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.load_yaml_button.clicked.connect(self.on_load_yaml)
        self.save_yaml_button.clicked.connect(self.on_save_yaml)
        self.refresh_button.clicked.connect(self.on_refresh_preview)
        self.run_compare_button.clicked.connect(self.on_run_compare)
        self.load_bundle_button.clicked.connect(self.on_load_bundle)
        self.clear_bundle_button.clicked.connect(self.on_clear_bundle)

    def _refresh_preview_from_config(self, config: ExperimentConfig, path: Path) -> None:
        preview = build_experiment_preview(
            config,
            config_path=path,
            run_selector="both",
        )
        self._apply_preview_summary(preview, path)

    def _apply_preview_summary(self, preview: ExperimentPreviewSummary, path: Path) -> None:
        self._current_config_path = path
        self._current_preview_summary = preview
        self.config_path_edit.setText(str(path))
        sequence_model = build_sequence_comparison_view_model(preview)
        comparison_model = build_timing_contrast_comparison_view_model(preview)
        self.sequence_panel.set_comparison_view_model(sequence_model)
        self.timing_contrast_panel.set_comparison_view_model(comparison_model)
        refreshed_text = datetime.now().isoformat(timespec="seconds")
        self.last_refreshed_label.setText(f"Last refreshed: {refreshed_text}")
        self.status_label.setText(f"Status: preview loaded from {path.name}")
        self._append_log(f"Loaded preview YAML: {path}")
        self._refresh_bundle_views()

    def _apply_bundle(
        self,
        bundle: ComparisonBundle,
        path: Path,
        file_info: dict[str, str],
    ) -> None:
        self._current_bundle = bundle
        self._current_bundle_path = path
        self._current_bundle_file_info = dict(file_info)
        self.bundle_path_edit.setText(str(path))
        loaded_text = datetime.now().isoformat(timespec="seconds")
        self.last_bundle_loaded_label.setText(f"Last bundle load: {loaded_text}")
        self.status_label.setText(f"Status: bundle loaded from {path.name}")
        self._append_log(f"Loaded comparison bundle: {path}")
        self._refresh_bundle_views()

    def _refresh_bundle_views(self) -> None:
        if self._current_bundle is None or self._current_bundle_path is None:
            self.results_panel.clear()
            self.comparison_summary_panel.clear()
            self.bundle_metadata_panel.clear()
            self._last_bundle_warning_signature = ()
            return

        results_model = build_results_comparison_view_model(self._current_bundle)
        comparison_model = build_comparison_summary_view_model(self._current_bundle)
        metadata_model = build_bundle_metadata_view_model(
            self._current_bundle,
            bundle_path=self._current_bundle_path,
            file_info=self._current_bundle_file_info,
            preview=self._current_preview_summary,
        )
        self.results_panel.set_comparison_view_model(results_model)
        self.comparison_summary_panel.set_view_model(comparison_model)
        self.bundle_metadata_panel.set_view_model(metadata_model)
        self.scene_panel.set_bundle(self._current_bundle)
        warning_signature = tuple(metadata_model.mismatch_warnings)
        if warning_signature != self._last_bundle_warning_signature:
            for warning in metadata_model.mismatch_warnings:
                self._append_log(f"Source mismatch warning: {warning}")
            self._last_bundle_warning_signature = warning_signature

    def _append_log(self, message: str) -> None:
        self.log_panel.append_log(message)

    def _start_compare_worker(self, config: ExperimentConfig, output_path: Path) -> None:
        thread = QThread(self)
        worker = CompareWorker(config, output_path)
        worker.moveToThread(thread)
        worker.log.connect(self._append_log)
        worker.finished.connect(self._handle_compare_finished)
        worker.failed.connect(self._handle_compare_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.started.connect(worker.run)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._handle_compare_thread_finished)
        self._compare_thread = thread
        self._compare_worker = worker
        self._set_running_state(True)
        self.status_label.setText(f"Status: running compare -> {output_path.name}")
        thread.start()

    def _handle_compare_finished(self, _summary: object, output_path: object) -> None:
        path = Path(str(output_path))
        self.status_label.setText(f"Status: compare finished -> {path.name}")
        self._append_log(f"Auto-loading comparison bundle: {path}")
        try:
            self.load_bundle_from_path(path)
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Bundle auto-load failed: {exc}")
            self._append_log(f"Bundle auto-load failed: {exc}")

    def _handle_compare_failed(self, message: str, traceback_text: str) -> None:
        self.status_label.setText(f"Status: compare failed: {message}")
        self._append_log(traceback_text)

    def _handle_compare_thread_finished(self) -> None:
        self._compare_thread = None
        self._compare_worker = None
        self._set_running_state(False)

    def _set_running_state(self, is_running: bool) -> None:
        enabled = not is_running
        self.experiment_editor.setEnabled(enabled)
        self.load_yaml_button.setEnabled(enabled)
        self.save_yaml_button.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)
        self.run_compare_button.setEnabled(enabled)
        self.load_bundle_button.setEnabled(enabled)
        self.clear_bundle_button.setEnabled(enabled)

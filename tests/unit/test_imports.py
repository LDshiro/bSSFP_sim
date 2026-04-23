"""Import tests for the package modules used through Chapter 7."""

from __future__ import annotations

import importlib
import importlib.util


def test_main_modules_import() -> None:
    module_names = [
        "bssfpviz",
        "bssfpviz.core",
        "bssfpviz.core.bloch",
        "bssfpviz.core.propagators",
        "bssfpviz.core.reference",
        "bssfpviz.core.rf",
        "bssfpviz.core.segments",
        "bssfpviz.core.steady_state",
        "bssfpviz.io.comparison_hdf5",
        "bssfpviz.io.hdf5_store",
        "bssfpviz.io",
        "bssfpviz.models.comparison",
        "bssfpviz.models.config",
        "bssfpviz.models.run_config",
        "bssfpviz.models.results",
        "bssfpviz.sequences",
        "bssfpviz.sequences.bssfp",
        "bssfpviz.sequences.fse_contrast",
        "bssfpviz.sequences.fse_common",
        "bssfpviz.sequences.bssfp.runner",
        "bssfpviz.sequences.fastse",
        "bssfpviz.sequences.fastse.runner",
        "bssfpviz.sequences.vfa_fse",
        "bssfpviz.sequences.vfa_fse.runner",
        "bssfpviz.viz",
        "bssfpviz.workflows.compare",
        "bssfpviz.workflows.compare_cli",
        "bssfpviz.workflows.compute_cli",
        "bssfpviz.workflows.compute_dataset",
        "bssfpviz.workflows.demo_dataset",
        "bssfpviz.workflows.preview",
        "bssfpviz.workflows.preview_cli",
        "bssfpviz.workflows.run_compute",
        "bssfpviz.workflows",
    ]

    if importlib.util.find_spec("PySide6") is not None:
        module_names.extend(
            [
                "bssfpviz.app.main",
                "bssfpviz.gui.adapters",
                "bssfpviz.gui.animation_view_model",
                "bssfpviz.gui.bookmark_panel",
                "bssfpviz.gui.bundle_metadata_panel",
                "bssfpviz.gui.bundle_view_models",
                "bssfpviz.gui.compare_worker",
                "bssfpviz.gui.comparison_controller",
                "bssfpviz.gui.comparison_panel",
                "bssfpviz.gui.comparison_summary_panel",
                "bssfpviz.gui.compute_worker",
                "bssfpviz.gui.config_editor",
                "bssfpviz.gui.dataset_view_model",
                "bssfpviz.gui.experiment_editor",
                "bssfpviz.gui.export_service",
                "bssfpviz.gui.generic_playback_controller",
                "bssfpviz.gui.generic_preview_window",
                "bssfpviz.gui.generic_scene_panel",
                "bssfpviz.gui.log_panel",
                "bssfpviz.gui.main_window",
                "bssfpviz.gui.metadata_panel",
                "bssfpviz.gui.playback_bar",
                "bssfpviz.gui.playback_controller",
                "bssfpviz.gui.preview_view_models",
                "bssfpviz.gui.profile_panel",
                "bssfpviz.gui.results_panel",
                "bssfpviz.gui.sequence_panel",
                "bssfpviz.gui.scene_panel",
                "bssfpviz.gui.session_state",
                "bssfpviz.gui.timing_contrast_panel",
                "bssfpviz.io.session_json",
            ]
        )

    for module_name in module_names:
        assert importlib.import_module(module_name) is not None

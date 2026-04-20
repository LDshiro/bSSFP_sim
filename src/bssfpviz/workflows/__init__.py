"""Workflow namespace for Chapter 3 and Chapter 4 compute helpers."""

from bssfpviz.workflows.compare import ComparisonSummary, run_comparison
from bssfpviz.workflows.compute_dataset import (
    compute_dataset,
    compute_late_cycle_error,
    make_chapter3_demo_config,
)
from bssfpviz.workflows.demo_dataset import make_demo_dataset, write_demo_hdf5
from bssfpviz.workflows.preview import (
    ExperimentPreviewSummary,
    SequencePreviewSummary,
    build_experiment_preview,
    build_run_preview,
)
from bssfpviz.workflows.run_compute import ComputeSummary, run_compute

__all__ = [
    "ComparisonSummary",
    "ComputeSummary",
    "ExperimentPreviewSummary",
    "SequencePreviewSummary",
    "build_experiment_preview",
    "build_run_preview",
    "compute_dataset",
    "compute_late_cycle_error",
    "make_chapter3_demo_config",
    "make_demo_dataset",
    "run_comparison",
    "run_compute",
    "write_demo_hdf5",
]

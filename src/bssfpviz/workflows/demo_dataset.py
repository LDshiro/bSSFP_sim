"""Backward-compatible Chapter 3 demo dataset generation helpers."""

from __future__ import annotations

import argparse
from pathlib import Path

from bssfpviz.io.hdf5_store import peek_hdf5_summary, save_dataset
from bssfpviz.models.results import SimulationDataset
from bssfpviz.workflows.compute_dataset import compute_dataset, make_chapter3_demo_config

DEFAULT_OUTPUT_PATH = Path("data/generated/demo_run.h5")


def make_demo_dataset() -> SimulationDataset:
    """Create the Chapter 3 demo dataset used by tests and smoke runs."""
    return compute_dataset(make_chapter3_demo_config())


def write_demo_hdf5(path: str | Path = DEFAULT_OUTPUT_PATH) -> dict[str, object]:
    """Generate the demo dataset, save it, and return a summary."""
    output_path = Path(path)
    dataset = make_demo_dataset()
    save_dataset(output_path, dataset)
    return peek_hdf5_summary(output_path)


def main(argv: list[str] | None = None) -> int:
    """Generate `data/generated/demo_run.h5` and print a short summary."""
    parser = argparse.ArgumentParser(description="Generate a Chapter 3 demo HDF5 dataset.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output HDF5 path.",
    )
    args = parser.parse_args(argv)

    summary = write_demo_hdf5(args.output)
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

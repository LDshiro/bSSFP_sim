"""Generate the Chapter 3 demo HDF5 dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

from bssfpviz.io.hdf5_store import peek_hdf5_summary, save_dataset
from bssfpviz.workflows.compute_dataset import (
    compute_dataset,
    compute_late_cycle_error,
    make_chapter3_demo_config,
)

DEFAULT_OUTPUT_PATH = Path("data/generated/chapter3_demo.h5")


def main(argv: list[str] | None = None) -> int:
    """Compute the Chapter 3 demo dataset, save it, and print a short summary."""
    parser = argparse.ArgumentParser(description="Compute the Chapter 3 demo HDF5 dataset.")
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Output HDF5 path."
    )
    args = parser.parse_args(argv)

    dataset = compute_dataset(make_chapter3_demo_config())
    dataset.metadata.run_name = "chapter3_demo"
    dataset.metadata.user_notes = "Chapter 3 exact Bloch / steady-state demo dataset."
    save_dataset(args.output, dataset)

    summary = peek_hdf5_summary(args.output)
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"late_cycle_error: {compute_late_cycle_error(dataset):.6e}")
    print(f"profile_shape: {dataset.individual_profile_complex.shape}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line entry point for the Chapter 4 compute workflow."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from bssfpviz.models.run_config import RunConfig
from bssfpviz.workflows.run_compute import ComputeSummary, run_compute


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Chapter 4 compute CLI."""
    parser = argparse.ArgumentParser(description="Run the Chapter 4 Bloch compute workflow.")
    parser.add_argument("--config", type=Path, required=True, help="Input YAML config path.")
    parser.add_argument("--output", type=Path, required=True, help="Output HDF5 path.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing output file if it already exists.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the human-readable summary on stdout.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional JSON summary output path.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.output.exists() and not args.overwrite:
            raise FileExistsError(f"Output file already exists: {args.output}")

        config = RunConfig.from_yaml(args.config)
        summary = run_compute(config=config, output_path=args.output)

        if args.summary_json is not None:
            args.summary_json.parent.mkdir(parents=True, exist_ok=True)
            args.summary_json.write_text(
                json.dumps(summary.to_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )

        if not args.quiet:
            print(_format_summary(summary))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"bssfpviz-compute: {exc}", file=sys.stderr)
        return 1


def _format_summary(summary: ComputeSummary) -> str:
    return "\n".join(
        [
            f"case_name: {summary.case_name}",
            f"output_path: {summary.output_path}",
            f"n_acquisitions: {summary.n_acquisitions}",
            f"n_delta_f: {summary.n_delta_f}",
            f"n_time_samples: {summary.n_time_samples}",
            f"individual_profile_abs_min: {summary.min_profile_individual:.6e}",
            f"individual_profile_abs_max: {summary.max_profile_individual:.6e}",
            f"sos_profile_abs_min: {summary.min_profile_sos:.6e}",
            f"sos_profile_abs_max: {summary.max_profile_sos:.6e}",
            f"elapsed_seconds: {summary.elapsed_seconds:.6f}",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())

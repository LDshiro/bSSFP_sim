"""Command-line entry point for the generic comparison workflow."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from bssfpviz.models.comparison import ExperimentConfig
from bssfpviz.workflows.compare import ComparisonSummary, run_comparison


def main(argv: Sequence[str] | None = None) -> int:
    """Run the generic comparison workflow."""
    parser = argparse.ArgumentParser(description="Run the generic MRI comparison workflow.")
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

        config = ExperimentConfig.from_yaml(args.config)
        summary = run_comparison(config=config, output_path=args.output)

        summary_json_path = args.summary_json
        if summary_json_path is None and config.output.summary_json:
            summary_json_path = Path(str(config.output.summary_json))
        if summary_json_path is not None:
            summary_json_path.parent.mkdir(parents=True, exist_ok=True)
            summary_json_path.write_text(
                json.dumps(summary.to_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )

        if not args.quiet:
            print(_format_summary(summary))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"bssfpviz-compare: {exc}", file=sys.stderr)
        return 1


def _format_summary(summary: ComparisonSummary) -> str:
    derived_ratio_lines = [
        f"derived_ratio.{key}: {value:.6e}" for key, value in sorted(summary.derived_ratios.items())
    ]
    matched_lines = [
        f"matched_constraint.{key}: {value}"
        for key, value in sorted(summary.matched_constraints_summary.items())
    ]
    return "\n".join(
        [
            f"comparison_scope: {summary.comparison_scope}",
            f"output_path: {summary.output_path}",
            f"run_a_family: {summary.run_a_family}",
            f"run_b_family: {summary.run_b_family}",
            f"run_a_case_name: {summary.run_a_case_name}",
            f"run_b_case_name: {summary.run_b_case_name}",
            f"elapsed_seconds: {summary.elapsed_seconds:.6f}",
            *matched_lines,
            *derived_ratio_lines,
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())

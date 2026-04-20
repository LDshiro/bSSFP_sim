"""Command-line entry point for the sequence preview workflow."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from bssfpviz.models.comparison import ExperimentConfig
from bssfpviz.workflows.preview import build_experiment_preview


def main(argv: Sequence[str] | None = None) -> int:
    """Generate sequence preview JSON for one experiment config."""
    parser = argparse.ArgumentParser(description="Generate preview JSON for comparison configs.")
    parser.add_argument("--config", type=Path, required=True, help="Input YAML config path.")
    parser.add_argument(
        "--run",
        type=str,
        default="both",
        help="Preview branch selector: run_a, run_b, or both.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output JSON path.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing output file if it already exists.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.output.exists() and not args.overwrite:
            raise FileExistsError(f"Output file already exists: {args.output}")

        config = ExperimentConfig.from_yaml(args.config)
        preview = build_experiment_preview(
            config,
            config_path=args.config,
            run_selector=args.run,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(preview.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"preview_output: {args.output}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"bssfpviz-preview: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

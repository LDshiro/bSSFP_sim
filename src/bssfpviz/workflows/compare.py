"""Generic comparison workflow for sequence-family experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

import numpy as np

from bssfpviz.io.comparison_hdf5 import save_comparison_bundle
from bssfpviz.models.comparison import (
    ComparisonBundle,
    ExperimentConfig,
    SequenceFamily,
    SimulationResult,
)
from bssfpviz.models.run_config import RunConfig
from bssfpviz.sequences.bssfp.runner import run_bssfp_simulation


@dataclass(slots=True)
class ComparisonSummary:
    """High-level summary for one comparison run."""

    comparison_scope: str
    output_path: Path
    run_a_family: str
    run_b_family: str
    run_a_case_name: str
    run_b_case_name: str
    elapsed_seconds: float
    ratio_sos_peak_b_over_a: float
    ratio_individual_peak_b_over_a: float

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        data = asdict(self)
        data["output_path"] = str(self.output_path)
        return data


def run_comparison(config: ExperimentConfig, output_path: Path) -> ComparisonSummary:
    """Execute a comparison experiment and write a generic HDF5 bundle."""
    config.validate_supported_families({SequenceFamily.BSSFP})
    start_time = perf_counter()
    run_a = _run_experiment_branch(
        config.run_a.to_run_config(config.common_physics),
        config.run_a.label,
    )
    run_b = _run_experiment_branch(
        config.run_b.to_run_config(config.common_physics),
        config.run_b.label,
    )

    bundle = _build_comparison_bundle(config, run_a, run_b)
    save_comparison_bundle(output_path, bundle)

    elapsed_seconds = perf_counter() - start_time
    return ComparisonSummary(
        comparison_scope=config.comparison_scope,
        output_path=output_path,
        run_a_family=run_a.sequence_family.value,
        run_b_family=run_b.sequence_family.value,
        run_a_case_name=run_a.case_name,
        run_b_case_name=run_b.case_name,
        elapsed_seconds=elapsed_seconds,
        ratio_sos_peak_b_over_a=float(bundle.derived_ratios["sos_peak_ratio_b_over_a"]),
        ratio_individual_peak_b_over_a=float(
            bundle.derived_ratios["individual_peak_ratio_b_over_a"]
        ),
    )


def _run_experiment_branch(run_config: RunConfig, label: str) -> SimulationResult:
    return run_bssfp_simulation(run_config, run_label=label)


def _build_comparison_bundle(
    config: ExperimentConfig,
    run_a: SimulationResult,
    run_b: SimulationResult,
) -> ComparisonBundle:
    sos_a = _max_observable(run_a, "sos_abs")
    sos_b = _max_observable(run_b, "sos_abs")
    individual_a = _max_observable(run_a, "individual_abs")
    individual_b = _max_observable(run_b, "individual_abs")
    n_delta_a = int(run_a.scalars.get("n_delta_f", 0))
    n_delta_b = int(run_b.scalars.get("n_delta_f", 0))
    n_acq_a = int(run_a.scalars.get("n_acquisitions", 0))
    n_acq_b = int(run_b.scalars.get("n_acquisitions", 0))

    return ComparisonBundle(
        comparison_scope=config.comparison_scope,
        comparison_modes=config.comparison_modes,
        run_a=run_a,
        run_b=run_b,
        matched_constraints_summary={
            "delta_n_delta_f": n_delta_b - n_delta_a,
            "delta_n_acquisitions": n_acq_b - n_acq_a,
            "delta_sos_peak": sos_b - sos_a,
            "delta_individual_peak": individual_b - individual_a,
        },
        derived_ratios={
            "sos_peak_ratio_b_over_a": _safe_ratio(sos_b, sos_a),
            "individual_peak_ratio_b_over_a": _safe_ratio(individual_b, individual_a),
        },
        report_metadata={
            "status": "comparison_ready",
            "supported_families": "BSSFP",
        },
    )


def _max_observable(result: SimulationResult, key: str) -> float:
    array = np.asarray(result.observables[key])
    return float(np.max(np.abs(array)))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if np.isclose(denominator, 0.0):
        return float("inf")
    return float(numerator / denominator)

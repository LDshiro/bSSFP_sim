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
    ExperimentRunConfig,
    ScalarValue,
    SequenceFamily,
    SimulationResult,
)
from bssfpviz.sequences.bssfp.runner import run_bssfp_simulation
from bssfpviz.sequences.fastse.runner import run_fastse_simulation


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
    matched_constraints_summary: dict[str, ScalarValue]
    derived_ratios: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        data = asdict(self)
        data["output_path"] = str(self.output_path)
        return data


def run_comparison(config: ExperimentConfig, output_path: Path) -> ComparisonSummary:
    """Execute a comparison experiment and write a generic HDF5 bundle."""
    config.validate_supported_families({SequenceFamily.BSSFP, SequenceFamily.FASTSE})
    start_time = perf_counter()
    run_a = _run_experiment_branch(
        config.run_a,
        config=config,
    )
    run_b = _run_experiment_branch(
        config.run_b,
        config=config,
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
        matched_constraints_summary=dict(bundle.matched_constraints_summary),
        derived_ratios=dict(bundle.derived_ratios),
    )


def _run_experiment_branch(
    run_config: ExperimentRunConfig,
    *,
    config: ExperimentConfig,
) -> SimulationResult:
    if run_config.sequence_family == SequenceFamily.BSSFP:
        if run_config.bssfp is None:
            msg = "Missing bssfp configuration for BSSFP run."
            raise ValueError(msg)
        return run_bssfp_simulation(
            run_config.bssfp.to_run_config(config.common_physics),
            run_label=run_config.label,
        )
    if run_config.sequence_family == SequenceFamily.FASTSE:
        if run_config.fastse is None:
            msg = "Missing fastse configuration for FASTSE run."
            raise ValueError(msg)
        return run_fastse_simulation(
            run_config.fastse,
            config.common_physics,
            run_label=run_config.label,
        )
    msg = f"Unsupported sequence family for compare workflow: {run_config.sequence_family.value}"
    raise ValueError(msg)


def _build_comparison_bundle(
    config: ExperimentConfig,
    run_a: SimulationResult,
    run_b: SimulationResult,
) -> ComparisonBundle:
    if run_a.sequence_family != run_b.sequence_family:
        msg = "Mixed-family compare is not supported in this phase."
        raise ValueError(msg)

    if run_a.sequence_family == SequenceFamily.BSSFP:
        matched_constraints_summary, derived_ratios = _build_bssfp_metrics(run_a, run_b)
    elif run_a.sequence_family == SequenceFamily.FASTSE:
        matched_constraints_summary, derived_ratios = _build_fastse_metrics(run_a, run_b)
    else:
        msg = f"Unsupported comparison family: {run_a.sequence_family.value}"
        raise ValueError(msg)

    return ComparisonBundle(
        comparison_scope=config.comparison_scope,
        comparison_modes=config.comparison_modes,
        run_a=run_a,
        run_b=run_b,
        matched_constraints_summary=matched_constraints_summary,
        derived_ratios=derived_ratios,
        report_metadata={
            "status": "comparison_ready",
            "supported_families": run_a.sequence_family.value,
            "same_family_only": "true",
        },
    )


def _build_bssfp_metrics(
    run_a: SimulationResult,
    run_b: SimulationResult,
) -> tuple[dict[str, ScalarValue], dict[str, float]]:
    sos_a = _max_observable(run_a, "sos_abs")
    sos_b = _max_observable(run_b, "sos_abs")
    individual_a = _max_observable(run_a, "individual_abs")
    individual_b = _max_observable(run_b, "individual_abs")
    n_delta_a = int(run_a.scalars.get("n_delta_f", 0))
    n_delta_b = int(run_b.scalars.get("n_delta_f", 0))
    n_acq_a = int(run_a.scalars.get("n_acquisitions", 0))
    n_acq_b = int(run_b.scalars.get("n_acquisitions", 0))
    return (
        {
            "delta_n_delta_f": n_delta_b - n_delta_a,
            "delta_n_acquisitions": n_acq_b - n_acq_a,
            "delta_sos_peak": sos_b - sos_a,
            "delta_individual_peak": individual_b - individual_a,
        },
        {
            "sos_peak_ratio_b_over_a": _safe_ratio(sos_b, sos_a),
            "individual_peak_ratio_b_over_a": _safe_ratio(individual_b, individual_a),
        },
    )


def _build_fastse_metrics(
    run_a: SimulationResult,
    run_b: SimulationResult,
) -> tuple[dict[str, ScalarValue], dict[str, float]]:
    echo_peak_a = float(run_a.scalars.get("echo_peak_abs", 0.0))
    echo_peak_b = float(run_b.scalars.get("echo_peak_abs", 0.0))
    fid_peak_a = float(run_a.scalars.get("fid_peak_abs", 0.0))
    fid_peak_b = float(run_b.scalars.get("fid_peak_abs", 0.0))
    etl_a = int(run_a.scalars.get("etl", 0))
    etl_b = int(run_b.scalars.get("etl", 0))
    return (
        {
            "delta_etl": etl_b - etl_a,
            "delta_echo_peak_abs": echo_peak_b - echo_peak_a,
            "delta_fid_peak_abs": fid_peak_b - fid_peak_a,
        },
        {
            "echo_peak_ratio_b_over_a": _safe_ratio(echo_peak_b, echo_peak_a),
            "fid_peak_ratio_b_over_a": _safe_ratio(fid_peak_b, fid_peak_a),
        },
    )


def _max_observable(result: SimulationResult, key: str) -> float:
    array = np.asarray(result.observables[key])
    return float(np.max(np.abs(array)))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if np.isclose(denominator, 0.0):
        return float("inf")
    return float(numerator / denominator)

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
from bssfpviz.sequences.vfa_fse.runner import run_vfa_fse_simulation


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
    report_metadata: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        data = asdict(self)
        data["output_path"] = str(self.output_path)
        return data


def run_comparison(config: ExperimentConfig, output_path: Path) -> ComparisonSummary:
    """Execute a comparison experiment and write a generic HDF5 bundle."""
    config.validate_supported_families(
        {SequenceFamily.BSSFP, SequenceFamily.FASTSE, SequenceFamily.VFA_FSE}
    )
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
        report_metadata=dict(bundle.report_metadata),
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
    if run_config.sequence_family == SequenceFamily.VFA_FSE:
        if run_config.vfa_fse is None:
            msg = "Missing vfa_fse configuration for VFA_FSE run."
            raise ValueError(msg)
        return run_vfa_fse_simulation(
            run_config.vfa_fse,
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
    report_metadata = {
        "status": "comparison_ready",
        "run_a_family": run_a.sequence_family.value,
        "run_b_family": run_b.sequence_family.value,
        "run_a_te_contrast_definition": str(
            run_a.family_metadata.get("te_contrast_definition", "N/A")
        ),
        "run_b_te_contrast_definition": str(
            run_b.family_metadata.get("te_contrast_definition", "N/A")
        ),
    }

    if run_a.sequence_family == run_b.sequence_family == SequenceFamily.BSSFP:
        matched_constraints_summary, derived_ratios = _build_bssfp_metrics(run_a, run_b)
        report_metadata["comparison_family_mode"] = "same_family"
        report_metadata["supported_families"] = "BSSFP"
    elif _is_supported_fse_like_pair(run_a.sequence_family, run_b.sequence_family):
        matched_constraints_summary, derived_ratios = _build_fse_like_metrics(run_a, run_b)
        report_metadata["comparison_family_mode"] = (
            "same_family" if run_a.sequence_family == run_b.sequence_family else "mixed_family"
        )
        report_metadata["supported_families"] = (
            f"{run_a.sequence_family.value},{run_b.sequence_family.value}"
        )
    else:
        msg = (
            "Mixed-family compare is supported in this phase only for "
            "FASTSE <-> VFA_FSE physics-only comparisons."
        )
        raise ValueError(msg)

    return ComparisonBundle(
        comparison_scope=config.comparison_scope,
        comparison_modes=config.comparison_modes,
        run_a=run_a,
        run_b=run_b,
        matched_constraints_summary=matched_constraints_summary,
        derived_ratios=derived_ratios,
        report_metadata=report_metadata,
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


def _build_fse_like_metrics(
    run_a: SimulationResult,
    run_b: SimulationResult,
) -> tuple[dict[str, ScalarValue], dict[str, float]]:
    echo_peak_a = float(run_a.scalars.get("echo_peak_abs", 0.0))
    echo_peak_b = float(run_b.scalars.get("echo_peak_abs", 0.0))
    fid_peak_a = float(run_a.scalars.get("fid_peak_abs", 0.0))
    fid_peak_b = float(run_b.scalars.get("fid_peak_abs", 0.0))
    etl_a = int(run_a.scalars.get("etl", 0))
    etl_b = int(run_b.scalars.get("etl", 0))
    te_center_a = float(run_a.scalars.get("te_center_k_ms", 0.0))
    te_center_b = float(run_b.scalars.get("te_center_k_ms", 0.0))
    te_contrast_a = _coerce_te_contrast_scalar(run_a)
    te_contrast_b = _coerce_te_contrast_scalar(run_b)
    esp_a = float(run_a.scalars.get("esp_ms", 0.0))
    esp_b = float(run_b.scalars.get("esp_ms", 0.0))
    te_contrast_epsilon_ms = max(5.0, esp_a, esp_b)
    delta_te_contrast_ms = (
        te_contrast_b - te_contrast_a
        if np.isfinite(te_contrast_a) and np.isfinite(te_contrast_b)
        else float("nan")
    )
    return (
        {
            "delta_etl": etl_b - etl_a,
            "delta_te_center_k_ms": te_center_b - te_center_a,
            "delta_te_contrast_ms": delta_te_contrast_ms,
            "te_contrast_epsilon_ms": te_contrast_epsilon_ms,
            "te_contrast_is_matched": (
                bool(abs(delta_te_contrast_ms) <= te_contrast_epsilon_ms)
                if np.isfinite(delta_te_contrast_ms)
                else False
            ),
            "delta_echo_peak_abs": echo_peak_b - echo_peak_a,
            "delta_fid_peak_abs": fid_peak_b - fid_peak_a,
        },
        {
            "echo_peak_ratio_b_over_a": _safe_ratio(echo_peak_b, echo_peak_a),
            "fid_peak_ratio_b_over_a": _safe_ratio(fid_peak_b, fid_peak_a),
        },
    )


def _is_supported_fse_like_pair(
    family_a: SequenceFamily,
    family_b: SequenceFamily,
) -> bool:
    fse_like = {SequenceFamily.FASTSE, SequenceFamily.VFA_FSE}
    if family_a == family_b and family_a in fse_like:
        return True
    return {family_a, family_b} == fse_like


def _coerce_te_contrast_scalar(result: SimulationResult) -> float:
    value = result.scalars.get("te_contrast_ms")
    if value is None:
        value = result.scalars.get("te_equiv_busse_ms", result.scalars.get("te_center_k_ms", 0.0))
    return float(value)


def _max_observable(result: SimulationResult, key: str) -> float:
    array = np.asarray(result.observables[key])
    return float(np.max(np.abs(array)))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if np.isclose(denominator, 0.0):
        return float("inf")
    return float(numerator / denominator)

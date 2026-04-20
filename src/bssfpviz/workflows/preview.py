"""Sequence preview service for comparison experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from bssfpviz.models.comparison import ExperimentConfig, ExperimentRunConfig, SequenceFamily
from bssfpviz.sequences.fastse.sequence import (
    build_echo_time_s,
    build_fid_time_s,
    build_flip_train_deg,
    build_phase_train_deg,
    compute_te_center_k_ms,
)


@dataclass(slots=True)
class SequencePreviewSummary:
    """Preview payload for one experiment branch."""

    sequence_family: str
    run_label: str
    case_name: str
    warnings: list[str]
    sequence_description: dict[str, object]
    timing_summary: dict[str, object]
    family_preview: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary."""
        return asdict(self)


@dataclass(slots=True)
class ExperimentPreviewSummary:
    """Preview payload for one experiment config."""

    comparison_scope: str
    config_path: str
    runs: dict[str, SequencePreviewSummary]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary."""
        return {
            "comparison_scope": self.comparison_scope,
            "config_path": self.config_path,
            "runs": {key: value.to_dict() for key, value in self.runs.items()},
        }


def build_experiment_preview(
    config: ExperimentConfig,
    *,
    config_path: str | Path,
    run_selector: str = "both",
) -> ExperimentPreviewSummary:
    """Build sequence previews for one or both experiment branches."""
    selector = str(run_selector).strip().lower()
    if selector not in {"run_a", "run_b", "both"}:
        msg = "run_selector must be one of 'run_a', 'run_b', or 'both'."
        raise ValueError(msg)

    runs: dict[str, SequencePreviewSummary] = {}
    if selector in {"run_a", "both"}:
        runs["run_a"] = build_run_preview(config.run_a)
    if selector in {"run_b", "both"}:
        runs["run_b"] = build_run_preview(config.run_b)

    return ExperimentPreviewSummary(
        comparison_scope=config.comparison_scope,
        config_path=str(config_path),
        runs=runs,
    )


def build_run_preview(run_config: ExperimentRunConfig) -> SequencePreviewSummary:
    """Build a sequence preview summary for one run branch."""
    if run_config.sequence_family == SequenceFamily.BSSFP:
        return _build_bssfp_preview(run_config)
    if run_config.sequence_family == SequenceFamily.FASTSE:
        return _build_fastse_preview(run_config)
    msg = f"Unsupported sequence family for preview: {run_config.sequence_family.value}"
    raise ValueError(msg)


def _build_bssfp_preview(run_config: ExperimentRunConfig) -> SequencePreviewSummary:
    if run_config.bssfp is None:
        msg = "Missing bssfp configuration for BSSFP preview."
        raise ValueError(msg)
    config = run_config.bssfp
    return SequencePreviewSummary(
        sequence_family=run_config.sequence_family.value,
        run_label=run_config.label,
        case_name=config.case_name,
        warnings=[],
        sequence_description={
            "sequence_variant": "BSSFP",
            "waveform_kind": config.sequence.waveform_kind,
            "phase_cycle_count": int(config.phase_cycles.values_deg.shape[0]),
        },
        timing_summary={
            "tr_ms": float(config.sequence.tr_s * 1.0e3),
            "rf_duration_ms": float(config.sequence.rf_duration_s * 1.0e3),
            "readout_time_ms": float(config.sequence.readout_time_s * 1.0e3),
        },
        family_preview={
            "phase_cycles_deg": config.phase_cycles.values_deg.tolist(),
            "delta_f_hz": {
                "start": float(config.sweep.start_hz),
                "stop": float(config.sweep.stop_hz),
                "count": int(config.sweep.count),
            },
        },
    )


def _build_fastse_preview(run_config: ExperimentRunConfig) -> SequencePreviewSummary:
    if run_config.fastse is None:
        msg = "Missing fastse configuration for FASTSE preview."
        raise ValueError(msg)
    config = run_config.fastse
    echo_time_ms = (build_echo_time_s(config) * 1.0e3).tolist()
    fid_time_ms = (build_fid_time_s(config) * 1.0e3).tolist()
    warnings = [
        "FASTSE preview uses the idealized hard-pulse baseline.",
        "Crusher timing, scan-time, and SAR models are not implemented in this phase.",
    ]
    return SequencePreviewSummary(
        sequence_family=run_config.sequence_family.value,
        run_label=run_config.label,
        case_name=config.case_name,
        warnings=warnings,
        sequence_description={
            "sequence_variant": config.sequence_variant,
            "dephasing_model": config.dephasing_model,
            "initial_state_mode": config.initial_state_mode,
            "timing_mode": config.timing_mode,
            "etl": int(config.etl),
            "n_iso": int(config.n_iso),
            "off_resonance_hz": float(config.off_resonance_hz),
        },
        timing_summary={
            "esp_ms": float(config.esp_ms),
            "te_center_k_ms": float(compute_te_center_k_ms(config)),
            "te_nominal_ms": (
                None if config.te_nominal_ms is None else float(config.te_nominal_ms)
            ),
            "sample_count_echo": int(config.etl),
            "sample_count_fid": int(config.etl),
        },
        family_preview={
            "flip_train_deg": build_flip_train_deg(config).tolist(),
            "phase_train_deg": build_phase_train_deg(config).tolist(),
            "echo_time_ms": echo_time_ms,
            "fid_time_ms": fid_time_ms,
            "esp_ms": float(config.esp_ms),
            "te_center_k_ms": float(compute_te_center_k_ms(config)),
            "te_nominal_ms": (
                None if config.te_nominal_ms is None else float(config.te_nominal_ms)
            ),
            "sample_count_echo": int(config.etl),
            "sample_count_fid": int(config.etl),
        },
    )

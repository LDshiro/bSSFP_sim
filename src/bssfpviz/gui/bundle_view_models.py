"""Bundle-driven view models for the generic comparison inspector shell."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from bssfpviz.models.comparison import (
    ComparisonBundle,
    ScalarValue,
    SequenceFamily,
    SimulationResult,
)
from bssfpviz.workflows.preview import ExperimentPreviewSummary

NA_TEXT = "N/A"
RESULTS_NOTE_TEXT = (
    "Read-only bundle view. Generate comparison bundles with bssfpviz-compare."
)
COMPARISON_NOTE_TEXT = "Comparison summary is read from the loaded bundle."


@dataclass(slots=True, frozen=True)
class PlotSeries:
    """One plotted line series."""

    key: str
    label: str
    x_values: np.ndarray
    y_values: np.ndarray
    color: str
    dashed: bool = False


@dataclass(slots=True, frozen=True)
class ResultsSummaryRow:
    """One summary row shown beside plotted bundle results."""

    key: str
    label: str
    value_text: str


@dataclass(slots=True, frozen=True)
class ResultsRunViewModel:
    """One run-side results view-model."""

    sequence_family: str
    run_label: str
    case_name: str
    primary_plot_title: str
    primary_x_label: str
    primary_y_label: str
    primary_series: tuple[PlotSeries, ...]
    secondary_plot_title: str | None
    secondary_x_label: str | None
    secondary_y_label: str | None
    secondary_series: tuple[PlotSeries, ...]
    summary_rows: tuple[ResultsSummaryRow, ...]
    extra_summary_rows: tuple[ResultsSummaryRow, ...]

    def summary_value_text_for_key(self, key: str) -> str:
        """Return the rendered value text for one summary key."""
        for row in (*self.summary_rows, *self.extra_summary_rows):
            if row.key == key:
                return row.value_text
        msg = f"Unsupported results summary key: {key}"
        raise KeyError(msg)


@dataclass(slots=True, frozen=True)
class ResultsDeltaRow:
    """One comparison-strip row for results rendering."""

    key: str
    label: str
    value_text: str


@dataclass(slots=True, frozen=True)
class ResultsComparisonViewModel:
    """Full side-by-side bundle results view-model."""

    run_a: ResultsRunViewModel
    run_b: ResultsRunViewModel
    delta_rows: tuple[ResultsDeltaRow, ...]
    note_text: str = RESULTS_NOTE_TEXT

    def delta_value_text_for_key(self, key: str) -> str:
        """Return the rendered value text for one delta key."""
        for row in self.delta_rows:
            if row.key == key:
                return row.value_text
        msg = f"Unsupported results delta key: {key}"
        raise KeyError(msg)


@dataclass(slots=True, frozen=True)
class ComparisonSectionRow:
    """One row inside the bundle comparison summary tables."""

    key: str
    label: str
    value_text: str
    highlight: bool = False


@dataclass(slots=True, frozen=True)
class ComparisonSectionViewModel:
    """One titled section inside the comparison summary tab."""

    key: str
    title: str
    rows: tuple[ComparisonSectionRow, ...]

    def value_text_for_key(self, key: str) -> str:
        """Return the rendered value for one row key."""
        for row in self.rows:
            if row.key == key:
                return row.value_text
        msg = f"Unsupported comparison section key: {key}"
        raise KeyError(msg)

    def highlight_for_key(self, key: str) -> bool:
        """Return whether one row is emphasized."""
        for row in self.rows:
            if row.key == key:
                return row.highlight
        msg = f"Unsupported comparison section key: {key}"
        raise KeyError(msg)


@dataclass(slots=True, frozen=True)
class ComparisonSummaryViewModel:
    """Structured bundle comparison summary view-model."""

    matched_constraints: ComparisonSectionViewModel
    derived_ratios: ComparisonSectionViewModel
    report_metadata: ComparisonSectionViewModel
    note_text: str = COMPARISON_NOTE_TEXT


@dataclass(slots=True, frozen=True)
class BundleMetadataViewModel:
    """Text-oriented bundle metadata view-model."""

    text: str
    mismatch_warnings: tuple[str, ...]


def build_results_comparison_view_model(bundle: ComparisonBundle) -> ResultsComparisonViewModel:
    """Build a plotting-oriented results view-model from one bundle."""
    run_a = _build_results_run_view_model(bundle.run_a)
    run_b = _build_results_run_view_model(bundle.run_b)
    delta_rows = _build_results_delta_rows(bundle)
    return ResultsComparisonViewModel(run_a=run_a, run_b=run_b, delta_rows=delta_rows)


def build_comparison_summary_view_model(bundle: ComparisonBundle) -> ComparisonSummaryViewModel:
    """Build a table-oriented view-model for bundle comparison summaries."""
    matched_rows = tuple(
        ComparisonSectionRow(
            key=key,
            label=key,
            value_text=_format_scalar(value),
            highlight=bool(key.endswith("_is_matched") and value is False),
        )
        for key, value in sorted(bundle.matched_constraints_summary.items())
    )
    ratio_rows = tuple(
        ComparisonSectionRow(
            key=key,
            label=key,
            value_text=_format_scalar(value, scientific=True),
            highlight=False,
        )
        for key, value in sorted(bundle.derived_ratios.items())
    )
    report_rows = tuple(
        ComparisonSectionRow(
            key=key,
            label=key,
            value_text=str(value),
            highlight=False,
        )
        for key, value in sorted(bundle.report_metadata.items())
    )
    return ComparisonSummaryViewModel(
        matched_constraints=ComparisonSectionViewModel(
            key="matched_constraints",
            title="Matched Constraints",
            rows=matched_rows,
        ),
        derived_ratios=ComparisonSectionViewModel(
            key="derived_ratios",
            title="Derived Ratios",
            rows=ratio_rows,
        ),
        report_metadata=ComparisonSectionViewModel(
            key="report_metadata",
            title="Report Metadata",
            rows=report_rows,
        ),
    )


def build_bundle_metadata_view_model(
    bundle: ComparisonBundle,
    *,
    bundle_path: Path,
    file_info: dict[str, str],
    preview: ExperimentPreviewSummary | None = None,
) -> BundleMetadataViewModel:
    """Build a text metadata summary for one loaded bundle."""
    mismatch_warnings = tuple(_build_preview_mismatch_warnings(bundle, preview=preview))
    lines = [
        "Bundle Metadata",
        f"  bundle_path: {bundle_path}",
        f"  schema_kind: {file_info.get('schema_kind', '')}",
        f"  comparison_schema_version: {file_info.get('comparison_schema_version', '')}",
        f"  app_name: {file_info.get('app_name', '')}",
        f"  app_version: {file_info.get('app_version', '')}",
        f"  comparison_scope: {bundle.comparison_scope}",
        f"  comparison_modes: {', '.join(bundle.comparison_modes)}",
        "",
        *_run_metadata_lines("Run A", bundle.run_a),
        "",
        *_run_metadata_lines("Run B", bundle.run_b),
        "",
        "Preview Source",
        f"  preview_loaded: {preview is not None}",
        f"  preview_config_path: {preview.config_path if preview is not None else ''}",
    ]
    if mismatch_warnings:
        lines.extend(["", "Warnings", *(f"  - {warning}" for warning in mismatch_warnings)])
    return BundleMetadataViewModel(text="\n".join(lines), mismatch_warnings=mismatch_warnings)


def _build_results_run_view_model(result: SimulationResult) -> ResultsRunViewModel:
    if result.sequence_family == SequenceFamily.BSSFP:
        return _build_bssfp_results_run_view_model(result)
    if result.sequence_family in {SequenceFamily.FASTSE, SequenceFamily.VFA_FSE}:
        return _build_fse_results_run_view_model(result)
    msg = f"Unsupported family for results view-model: {result.sequence_family.value}"
    raise ValueError(msg)


def _build_fse_results_run_view_model(result: SimulationResult) -> ResultsRunViewModel:
    echo_time_ms = np.asarray(result.axes["echo_time_s"], dtype=np.float64) * 1.0e3
    fid_time_ms = np.asarray(result.axes["fid_time_s"], dtype=np.float64) * 1.0e3
    echo_signal_abs = np.asarray(result.observables["echo_signal_abs"], dtype=np.float64)
    fid_signal_abs = np.asarray(result.observables["fid_signal_abs"], dtype=np.float64)
    summary_rows = (
        ResultsSummaryRow(
            "echo_peak_abs",
            "echo_peak_abs",
            _format_scalar(result.scalars.get("echo_peak_abs")),
        ),
        ResultsSummaryRow(
            "fid_peak_abs",
            "fid_peak_abs",
            _format_scalar(result.scalars.get("fid_peak_abs")),
        ),
        ResultsSummaryRow(
            "te_center_k_ms",
            "te_center_k_ms",
            _format_scalar(result.scalars.get("te_center_k_ms")),
        ),
        ResultsSummaryRow(
            "te_contrast_ms",
            "te_contrast_ms",
            _format_scalar(result.scalars.get("te_contrast_ms")),
        ),
        ResultsSummaryRow(
            "te_contrast_definition",
            "te_contrast_definition",
            str(result.family_metadata.get("te_contrast_definition", "")),
        ),
    )
    extra_rows: tuple[ResultsSummaryRow, ...] = ()
    if result.sequence_family == SequenceFamily.VFA_FSE:
        extra_rows = (
            ResultsSummaryRow(
                "te_equiv_busse_ms",
                "te_equiv_busse_ms",
                _format_scalar(result.scalars.get("te_equiv_busse_ms")),
            ),
            ResultsSummaryRow(
                "ft_wh2006",
                "ft_wh2006",
                _format_scalar(result.scalars.get("ft_wh2006")),
            ),
            ResultsSummaryRow(
                "te_contrast_wh_ms",
                "te_contrast_wh_ms",
                _format_scalar(result.scalars.get("te_contrast_wh_ms")),
            ),
        )
    return ResultsRunViewModel(
        sequence_family=result.sequence_family.value,
        run_label=result.run_label,
        case_name=result.case_name,
        primary_plot_title="Echo / FID",
        primary_x_label="t [ms]",
        primary_y_label="Signal magnitude",
        primary_series=(
            PlotSeries(
                key="echo_signal_abs",
                label="Echo",
                x_values=echo_time_ms,
                y_values=echo_signal_abs,
                color="#1f77b4",
            ),
            PlotSeries(
                key="fid_signal_abs",
                label="FID",
                x_values=fid_time_ms,
                y_values=fid_signal_abs,
                color="#d95f02",
                dashed=True,
            ),
        ),
        secondary_plot_title=None,
        secondary_x_label=None,
        secondary_y_label=None,
        secondary_series=(),
        summary_rows=summary_rows,
        extra_summary_rows=extra_rows,
    )


def _build_bssfp_results_run_view_model(result: SimulationResult) -> ResultsRunViewModel:
    delta_f_hz = np.asarray(result.axes["delta_f_hz"], dtype=np.float64)
    sos_abs = np.asarray(result.observables["sos_abs"], dtype=np.float64)
    individual_abs = np.asarray(result.observables["individual_abs"], dtype=np.float64)
    secondary_series = tuple(
        PlotSeries(
            key=f"individual_abs_{acquisition_index}",
            label=f"acq {acquisition_index}",
            x_values=delta_f_hz,
            y_values=np.asarray(individual_abs[:, acquisition_index], dtype=np.float64),
            color=_BSSFP_COLORS[acquisition_index % len(_BSSFP_COLORS)],
        )
        for acquisition_index in range(individual_abs.shape[1])
    )
    return ResultsRunViewModel(
        sequence_family=result.sequence_family.value,
        run_label=result.run_label,
        case_name=result.case_name,
        primary_plot_title="SoS Profile",
        primary_x_label="Δf [Hz]",
        primary_y_label="Signal magnitude",
        primary_series=(
            PlotSeries(
                key="sos_abs",
                label="SoS",
                x_values=delta_f_hz,
                y_values=sos_abs,
                color="#1c4f8a",
            ),
        ),
        secondary_plot_title="Individual Profiles",
        secondary_x_label="Δf [Hz]",
        secondary_y_label="Signal magnitude",
        secondary_series=secondary_series,
        summary_rows=(
            ResultsSummaryRow(
                "n_delta_f",
                "n_delta_f",
                _format_scalar(result.scalars.get("n_delta_f")),
            ),
            ResultsSummaryRow(
                "n_acquisitions",
                "n_acquisitions",
                _format_scalar(result.scalars.get("n_acquisitions")),
            ),
            ResultsSummaryRow("sos_peak", "sos_peak", _format_scalar(np.max(sos_abs))),
            ResultsSummaryRow(
                "individual_peak",
                "individual_peak",
                _format_scalar(np.max(np.abs(individual_abs))),
            ),
        ),
        extra_summary_rows=(),
    )


def _build_results_delta_rows(bundle: ComparisonBundle) -> tuple[ResultsDeltaRow, ...]:
    keys: tuple[str, ...]
    if bundle.run_a.sequence_family == bundle.run_b.sequence_family == SequenceFamily.BSSFP:
        keys = (
            "delta_sos_peak",
            "delta_individual_peak",
            "sos_peak_ratio_b_over_a",
            "individual_peak_ratio_b_over_a",
        )
    else:
        keys = (
            "delta_te_contrast_ms",
            "delta_echo_peak_abs",
            "delta_fid_peak_abs",
            "echo_peak_ratio_b_over_a",
            "fid_peak_ratio_b_over_a",
        )
    rows: list[ResultsDeltaRow] = []
    for key in keys:
        if key in bundle.matched_constraints_summary:
            value = bundle.matched_constraints_summary[key]
            rows.append(ResultsDeltaRow(key=key, label=key, value_text=_format_scalar(value)))
        elif key in bundle.derived_ratios:
            value = bundle.derived_ratios[key]
            rows.append(
                ResultsDeltaRow(
                    key=key,
                    label=key,
                    value_text=_format_scalar(value, scientific=True),
                )
            )
        else:
            rows.append(ResultsDeltaRow(key=key, label=key, value_text=NA_TEXT))
    return tuple(rows)


def _build_preview_mismatch_warnings(
    bundle: ComparisonBundle,
    *,
    preview: ExperimentPreviewSummary | None,
) -> list[str]:
    if preview is None:
        return []
    warnings: list[str] = []
    preview_runs = (("run_a", bundle.run_a), ("run_b", bundle.run_b))
    for run_key, bundle_run in preview_runs:
        summary = preview.runs.get(run_key)
        if summary is None:
            warnings.append(f"{run_key}: preview source is missing this run.")
            continue
        if summary.sequence_family != bundle_run.sequence_family.value:
            warnings.append(
                f"{run_key}: preview family {summary.sequence_family} does not match "
                f"bundle family {bundle_run.sequence_family.value}."
            )
        if summary.run_label != bundle_run.run_label:
            warnings.append(
                f"{run_key}: preview label {summary.run_label!r} does not match "
                f"bundle label {bundle_run.run_label!r}."
            )
        if summary.case_name != bundle_run.case_name:
            warnings.append(
                f"{run_key}: preview case {summary.case_name!r} does not match "
                f"bundle case {bundle_run.case_name!r}."
            )
    return warnings


def _run_metadata_lines(title: str, result: SimulationResult) -> list[str]:
    lines = [
        title,
        f"  sequence_family: {result.sequence_family.value}",
        f"  run_label: {result.run_label}",
        f"  case_name: {result.case_name}",
        f"  description: {result.description}",
        "  family_metadata:",
    ]
    family_metadata = result.family_metadata or {}
    if family_metadata:
        for key, value in sorted(family_metadata.items()):
            lines.append(f"    {key}: {value}")
    else:
        lines.append("    -")
    return lines

def _format_scalar(
    value: ScalarValue | float | int | bool | None,
    *,
    scientific: bool = False,
) -> str:
    if value is None:
        return NA_TEXT
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            return NA_TEXT
        if scientific or (numeric_value != 0.0 and abs(numeric_value) < 1.0e-3):
            return f"{numeric_value:.3e}"
        return f"{numeric_value:.3f}"
    return str(value)


_BSSFP_COLORS = ("#1f77b4", "#d95f02", "#2ca02c", "#9467bd", "#8c564b")

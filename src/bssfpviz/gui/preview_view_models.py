"""Preview-specific view models for the generic inspector shell."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real

from bssfpviz.workflows.preview import ExperimentPreviewSummary, SequencePreviewSummary

NA_TEXT = "N/A"
NOT_IMPLEMENTED_TEXT = "Not implemented in this phase"
TIMING_NOTE_TEXT = "matched_TE_contrast is evaluated during compare execution."
SEQUENCE_NOTE_TEXT = "Preview-only sequence view. k-space timeline is not implemented yet."
_TIMING_ROW_SPECS: tuple[tuple[str, str], ...] = (
    ("tr_ms", "TR_ms"),
    ("esp_ms", "ESP_ms"),
    ("te_nominal_ms", "TE_nominal_ms"),
    ("te_center_k_ms", "TE_center_k_ms"),
    ("te_equiv_busse_ms", "TE_equiv_Busse_ms"),
    ("te_contrast_ms", "TE_contrast_ms"),
    ("rf_duration_ms", "rf_duration_ms"),
    ("readout_time_ms", "readout_time_ms"),
    ("ft_wh2006", "f_t_WH2006"),
    ("te_contrast_wh_ms", "TE_contrast_WH_ms"),
    ("tscan_s", "Tscan_s"),
)
_PRIMARY_ROW_KEYS = {
    "BSSFP": frozenset({"readout_time_ms"}),
    "FASTSE": frozenset({"te_center_k_ms", "te_contrast_ms"}),
    "VFA_FSE": frozenset({"te_equiv_busse_ms", "te_contrast_ms"}),
}
_PLACEHOLDER_ROW_KEYS = frozenset({"tscan_s"})
_DELTA_ROW_SPECS: tuple[tuple[str, str], ...] = (
    ("te_contrast_ms", "delta_te_contrast_ms"),
    ("te_center_k_ms", "delta_te_center_k_ms"),
    ("esp_ms", "delta_esp_ms"),
)


@dataclass(slots=True, frozen=True)
class TimingContrastRow:
    """One read-only timing or contrast row."""

    key: str
    label: str
    value_text: str
    numeric_value: float | None
    is_primary: bool = False


@dataclass(slots=True, frozen=True)
class TimingContrastViewModel:
    """Timing and contrast summary for one run branch."""

    sequence_family: str
    run_label: str
    case_name: str
    rows: tuple[TimingContrastRow, ...]
    warnings: tuple[str, ...]

    def value_text_for_key(self, key: str) -> str:
        """Return the display text for one timing row."""
        for row in self.rows:
            if row.key == key:
                return row.value_text
        msg = f"Unsupported timing row key: {key}"
        raise KeyError(msg)

    def numeric_value_for_key(self, key: str) -> float | None:
        """Return the numeric value for one timing row when available."""
        for row in self.rows:
            if row.key == key:
                return row.numeric_value
        msg = f"Unsupported timing row key: {key}"
        raise KeyError(msg)


@dataclass(slots=True, frozen=True)
class TimingContrastDeltaRow:
    """Comparison-strip row derived from Run A / Run B preview data."""

    key: str
    label: str
    value_text: str
    numeric_value: float | None
    highlight: bool = False


@dataclass(slots=True, frozen=True)
class TimingContrastComparisonViewModel:
    """Full side-by-side timing and contrast view-model."""

    run_a: TimingContrastViewModel
    run_b: TimingContrastViewModel
    delta_rows: tuple[TimingContrastDeltaRow, ...]
    note_text: str = TIMING_NOTE_TEXT

    def delta_value_text_for_key(self, key: str) -> str:
        """Return the display text for one delta row."""
        for row in self.delta_rows:
            if row.key == key:
                return row.value_text
        msg = f"Unsupported delta row key: {key}"
        raise KeyError(msg)


def build_timing_contrast_comparison_view_model(
    preview: ExperimentPreviewSummary,
) -> TimingContrastComparisonViewModel:
    """Build a GUI-friendly timing/contrast view-model from preview data."""
    run_a_summary = _require_run(preview, "run_a")
    run_b_summary = _require_run(preview, "run_b")
    run_a = _build_run_view_model(run_a_summary)
    run_b = _build_run_view_model(run_b_summary)
    return TimingContrastComparisonViewModel(
        run_a=run_a,
        run_b=run_b,
        delta_rows=_build_delta_rows(run_a, run_b),
    )


def _require_run(preview: ExperimentPreviewSummary, run_key: str) -> SequencePreviewSummary:
    try:
        return preview.runs[run_key]
    except KeyError as exc:
        msg = f"Preview summary is missing required run: {run_key}"
        raise ValueError(msg) from exc


def _build_run_view_model(summary: SequencePreviewSummary) -> TimingContrastViewModel:
    rows = tuple(_build_run_row(summary, key=key, label=label) for key, label in _TIMING_ROW_SPECS)
    return TimingContrastViewModel(
        sequence_family=summary.sequence_family,
        run_label=summary.run_label,
        case_name=summary.case_name,
        rows=rows,
        warnings=tuple(summary.warnings),
    )


def _build_run_row(summary: SequencePreviewSummary, *, key: str, label: str) -> TimingContrastRow:
    value_text, numeric_value = _resolve_value(summary, key)
    return TimingContrastRow(
        key=key,
        label=label,
        value_text=value_text,
        numeric_value=numeric_value,
        is_primary=key in _PRIMARY_ROW_KEYS.get(summary.sequence_family, frozenset()),
    )


def _resolve_value(
    summary: SequencePreviewSummary,
    key: str,
) -> tuple[str, float | None]:
    if key in _PLACEHOLDER_ROW_KEYS:
        return (NOT_IMPLEMENTED_TEXT, None)

    raw_value = summary.timing_summary.get(key)
    if raw_value is None:
        return (NA_TEXT, None)
    if isinstance(raw_value, Real) and not isinstance(raw_value, bool):
        numeric_value = float(raw_value)
        if not math.isfinite(numeric_value):
            return (NA_TEXT, None)
        return (_format_numeric(numeric_value), numeric_value)
    return (str(raw_value), None)


def _build_delta_rows(
    run_a: TimingContrastViewModel,
    run_b: TimingContrastViewModel,
) -> tuple[TimingContrastDeltaRow, ...]:
    delta_rows: list[TimingContrastDeltaRow] = []
    is_vfa_pair = run_a.sequence_family == run_b.sequence_family == "VFA_FSE"
    for source_key, label in _DELTA_ROW_SPECS:
        numeric_a = run_a.numeric_value_for_key(source_key)
        numeric_b = run_b.numeric_value_for_key(source_key)
        if numeric_a is None or numeric_b is None:
            delta_rows.append(
                TimingContrastDeltaRow(
                    key=source_key,
                    label=label,
                    value_text=NA_TEXT,
                    numeric_value=None,
                    highlight=False,
                )
            )
            continue
        delta_value = numeric_b - numeric_a
        delta_rows.append(
            TimingContrastDeltaRow(
                key=source_key,
                label=label,
                value_text=_format_numeric(delta_value),
                numeric_value=delta_value,
                highlight=is_vfa_pair and source_key == "te_contrast_ms",
            )
        )
    return tuple(delta_rows)


def _format_numeric(value: float) -> str:
    return f"{value:.3f}"


@dataclass(slots=True, frozen=True)
class SequenceTableRow:
    """One three-column row inside the sequence tab."""

    index_text: str
    value_a_text: str
    value_b_text: str


@dataclass(slots=True, frozen=True)
class SequenceTableSection:
    """One titled table section for sequence preview data."""

    key: str
    title: str
    column_labels: tuple[str, str, str]
    rows: tuple[SequenceTableRow, ...]

    def cell_text(self, row_index: int, column_index: int) -> str:
        """Return one rendered table cell."""
        row = self.rows[row_index]
        if column_index == 0:
            return row.index_text
        if column_index == 1:
            return row.value_a_text
        if column_index == 2:
            return row.value_b_text
        msg = f"Unsupported column index: {column_index}"
        raise IndexError(msg)


@dataclass(slots=True, frozen=True)
class SequenceSummaryRow:
    """One read-only summary row for the sequence tab."""

    key: str
    label: str
    value_text: str
    numeric_value: float | int | None


@dataclass(slots=True, frozen=True)
class SequenceRunViewModel:
    """One run-side sequence preview view-model."""

    sequence_family: str
    run_label: str
    case_name: str
    warnings: tuple[str, ...]
    primary_table: SequenceTableSection | None
    secondary_table: SequenceTableSection | None
    summary_title: str
    summary_rows: tuple[SequenceSummaryRow, ...]
    extra_summary_title: str | None
    extra_summary_rows: tuple[SequenceSummaryRow, ...]

    def summary_value_text_for_key(self, key: str) -> str:
        """Return the display text for one summary row."""
        for row in (*self.summary_rows, *self.extra_summary_rows):
            if row.key == key:
                return row.value_text
        msg = f"Unsupported summary row key: {key}"
        raise KeyError(msg)

    def summary_numeric_value_for_key(self, key: str) -> float | int | None:
        """Return the numeric value for one summary row when available."""
        for row in (*self.summary_rows, *self.extra_summary_rows):
            if row.key == key:
                return row.numeric_value
        msg = f"Unsupported summary row key: {key}"
        raise KeyError(msg)

    def table_cell_text(self, table_key: str, row_index: int, column_index: int) -> str:
        """Return one rendered cell from the requested table section."""
        if table_key == "primary":
            if self.primary_table is None:
                return NA_TEXT
            return self.primary_table.cell_text(row_index, column_index)
        if table_key == "secondary":
            if self.secondary_table is None:
                return NA_TEXT
            return self.secondary_table.cell_text(row_index, column_index)
        msg = f"Unsupported table key: {table_key}"
        raise KeyError(msg)


@dataclass(slots=True, frozen=True)
class SequenceComparisonDeltaRow:
    """One comparison-strip row for the sequence tab."""

    key: str
    label: str
    value_text: str
    numeric_value: float | int | None


@dataclass(slots=True, frozen=True)
class SequenceComparisonViewModel:
    """Full side-by-side sequence preview view-model."""

    run_a: SequenceRunViewModel
    run_b: SequenceRunViewModel
    delta_rows: tuple[SequenceComparisonDeltaRow, ...]
    note_text: str = SEQUENCE_NOTE_TEXT

    def delta_value_text_for_key(self, key: str) -> str:
        """Return the display text for one delta row."""
        for row in self.delta_rows:
            if row.key == key:
                return row.value_text
        msg = f"Unsupported sequence delta row key: {key}"
        raise KeyError(msg)


def build_sequence_comparison_view_model(
    preview: ExperimentPreviewSummary,
) -> SequenceComparisonViewModel:
    """Build a GUI-friendly sequence view-model from preview data."""
    run_a_summary = _require_run(preview, "run_a")
    run_b_summary = _require_run(preview, "run_b")
    run_a = _build_sequence_run_view_model(run_a_summary)
    run_b = _build_sequence_run_view_model(run_b_summary)
    return SequenceComparisonViewModel(
        run_a=run_a,
        run_b=run_b,
        delta_rows=_build_sequence_delta_rows(run_a, run_b),
    )


def _build_sequence_run_view_model(summary: SequencePreviewSummary) -> SequenceRunViewModel:
    if summary.sequence_family in {"FASTSE", "VFA_FSE"}:
        return _build_fse_sequence_run_view_model(summary)
    if summary.sequence_family == "BSSFP":
        return _build_bssfp_sequence_run_view_model(summary)
    msg = f"Unsupported sequence family for sequence preview: {summary.sequence_family}"
    raise ValueError(msg)


def _build_fse_sequence_run_view_model(summary: SequencePreviewSummary) -> SequenceRunViewModel:
    family_preview = summary.family_preview
    flip_train = _as_float_list(family_preview.get("flip_train_deg"))
    phase_train = _as_float_list(family_preview.get("phase_train_deg"))
    echo_time_ms = _as_float_list(family_preview.get("echo_time_ms"))
    fid_time_ms = _as_float_list(family_preview.get("fid_time_ms"))
    primary_table = SequenceTableSection(
        key="primary",
        title="Flip / Phase Train",
        column_labels=("Index", "Flip (deg)", "Phase (deg)"),
        rows=tuple(
            SequenceTableRow(
                index_text=str(row_index),
                value_a_text=_format_numeric(flip_value),
                value_b_text=_format_numeric(phase_value),
            )
            for row_index, (flip_value, phase_value) in enumerate(
                zip(flip_train, phase_train, strict=True)
            )
        ),
    )
    secondary_table = SequenceTableSection(
        key="secondary",
        title="Echo / FID Timing",
        column_labels=("Index", "Echo (ms)", "FID (ms)"),
        rows=tuple(
            SequenceTableRow(
                index_text=str(row_index + 1),
                value_a_text=_format_numeric(echo_value),
                value_b_text=_format_numeric(fid_value),
            )
            for row_index, (echo_value, fid_value) in enumerate(
                zip(echo_time_ms, fid_time_ms, strict=True)
            )
        ),
    )
    summary_rows = (
        SequenceSummaryRow(
            key="esp_ms",
            label="ESP_ms",
            value_text=_format_optional_float(family_preview.get("esp_ms")),
            numeric_value=_optional_numeric_value(family_preview.get("esp_ms")),
        ),
        SequenceSummaryRow(
            key="sample_count_echo",
            label="sample_count_echo",
            value_text=_format_optional_int(family_preview.get("sample_count_echo")),
            numeric_value=_optional_int_value(family_preview.get("sample_count_echo")),
        ),
        SequenceSummaryRow(
            key="sample_count_fid",
            label="sample_count_fid",
            value_text=_format_optional_int(family_preview.get("sample_count_fid")),
            numeric_value=_optional_int_value(family_preview.get("sample_count_fid")),
        ),
    )
    return SequenceRunViewModel(
        sequence_family=summary.sequence_family,
        run_label=summary.run_label,
        case_name=summary.case_name,
        warnings=tuple(summary.warnings),
        primary_table=primary_table,
        secondary_table=secondary_table,
        summary_title="Sequence Summary",
        summary_rows=summary_rows,
        extra_summary_title=None,
        extra_summary_rows=(),
    )


def _build_bssfp_sequence_run_view_model(summary: SequencePreviewSummary) -> SequenceRunViewModel:
    family_preview = summary.family_preview
    phase_cycles = _as_phase_cycle_rows(family_preview.get("phase_cycles_deg"))
    primary_table = SequenceTableSection(
        key="primary",
        title="Phase Cycles",
        column_labels=("Acq", "Pulse 0 (deg)", "Pulse 1 (deg)"),
        rows=tuple(
            SequenceTableRow(
                index_text=str(row_index),
                value_a_text=_format_numeric(float(row[0])),
                value_b_text=_format_numeric(float(row[1])),
            )
            for row_index, row in enumerate(phase_cycles)
        ),
    )
    summary_rows = (
        SequenceSummaryRow(
            key="tr_ms",
            label="TR_ms",
            value_text=_format_optional_float(summary.timing_summary.get("tr_ms")),
            numeric_value=_optional_numeric_value(summary.timing_summary.get("tr_ms")),
        ),
        SequenceSummaryRow(
            key="rf_duration_ms",
            label="rf_duration_ms",
            value_text=_format_optional_float(summary.timing_summary.get("rf_duration_ms")),
            numeric_value=_optional_numeric_value(summary.timing_summary.get("rf_duration_ms")),
        ),
        SequenceSummaryRow(
            key="readout_time_ms",
            label="readout_time_ms",
            value_text=_format_optional_float(summary.timing_summary.get("readout_time_ms")),
            numeric_value=_optional_numeric_value(summary.timing_summary.get("readout_time_ms")),
        ),
    )
    delta_f_summary = _as_mapping(family_preview.get("delta_f_hz"))
    extra_summary_rows = (
        SequenceSummaryRow(
            key="delta_f_start_hz",
            label="delta_f_start_hz",
            value_text=_format_optional_float(delta_f_summary.get("start")),
            numeric_value=_optional_numeric_value(delta_f_summary.get("start")),
        ),
        SequenceSummaryRow(
            key="delta_f_stop_hz",
            label="delta_f_stop_hz",
            value_text=_format_optional_float(delta_f_summary.get("stop")),
            numeric_value=_optional_numeric_value(delta_f_summary.get("stop")),
        ),
        SequenceSummaryRow(
            key="delta_f_count",
            label="delta_f_count",
            value_text=_format_optional_int(delta_f_summary.get("count")),
            numeric_value=_optional_int_value(delta_f_summary.get("count")),
        ),
    )
    return SequenceRunViewModel(
        sequence_family=summary.sequence_family,
        run_label=summary.run_label,
        case_name=summary.case_name,
        warnings=tuple(summary.warnings),
        primary_table=primary_table,
        secondary_table=None,
        summary_title="Timing Summary",
        summary_rows=summary_rows,
        extra_summary_title="Sweep Summary",
        extra_summary_rows=extra_summary_rows,
    )


def _build_sequence_delta_rows(
    run_a: SequenceRunViewModel,
    run_b: SequenceRunViewModel,
) -> tuple[SequenceComparisonDeltaRow, ...]:
    if run_a.sequence_family in {"FASTSE", "VFA_FSE"} and run_b.sequence_family in {
        "FASTSE",
        "VFA_FSE",
    }:
        return (
            _build_sequence_delta_row(
                key="esp_ms",
                label="delta_esp_ms",
                value_a=run_a.summary_numeric_value_for_key("esp_ms"),
                value_b=run_b.summary_numeric_value_for_key("esp_ms"),
                format_kind="float",
            ),
            _build_sequence_delta_row(
                key="sample_count_echo",
                label="delta_echo_count",
                value_a=run_a.summary_numeric_value_for_key("sample_count_echo"),
                value_b=run_b.summary_numeric_value_for_key("sample_count_echo"),
                format_kind="int",
            ),
            _build_sequence_delta_row(
                key="sample_count_fid",
                label="delta_fid_count",
                value_a=run_a.summary_numeric_value_for_key("sample_count_fid"),
                value_b=run_b.summary_numeric_value_for_key("sample_count_fid"),
                format_kind="int",
            ),
        )
    if run_a.sequence_family == run_b.sequence_family == "BSSFP":
        phase_cycle_count_a = (
            len(run_a.primary_table.rows) if run_a.primary_table is not None else 0
        )
        phase_cycle_count_b = (
            len(run_b.primary_table.rows) if run_b.primary_table is not None else 0
        )
        return (
            _build_sequence_delta_row(
                key="tr_ms",
                label="delta_tr_ms",
                value_a=run_a.summary_numeric_value_for_key("tr_ms"),
                value_b=run_b.summary_numeric_value_for_key("tr_ms"),
                format_kind="float",
            ),
            _build_sequence_delta_row(
                key="phase_cycle_count",
                label="delta_phase_cycle_count",
                value_a=phase_cycle_count_a,
                value_b=phase_cycle_count_b,
                format_kind="int",
            ),
            _build_sequence_delta_row(
                key="delta_f_count",
                label="delta_delta_f_count",
                value_a=run_a.summary_numeric_value_for_key("delta_f_count"),
                value_b=run_b.summary_numeric_value_for_key("delta_f_count"),
                format_kind="int",
            ),
        )
    return (
        SequenceComparisonDeltaRow(
            key="mixed_family_primary",
            label="delta_primary_metric",
            value_text=NA_TEXT,
            numeric_value=None,
        ),
        SequenceComparisonDeltaRow(
            key="mixed_family_secondary",
            label="delta_secondary_metric",
            value_text=NA_TEXT,
            numeric_value=None,
        ),
    )


def _build_sequence_delta_row(
    *,
    key: str,
    label: str,
    value_a: float | int | None,
    value_b: float | int | None,
    format_kind: str,
) -> SequenceComparisonDeltaRow:
    if value_a is None or value_b is None:
        return SequenceComparisonDeltaRow(
            key=key,
            label=label,
            value_text=NA_TEXT,
            numeric_value=None,
        )
    delta_value = value_b - value_a
    if format_kind == "int":
        value_text = str(int(delta_value))
    else:
        value_text = _format_numeric(float(delta_value))
    return SequenceComparisonDeltaRow(
        key=key,
        label=label,
        value_text=value_text,
        numeric_value=delta_value,
    )


def _as_float_list(value: object) -> tuple[float, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(float(item) for item in value)


def _format_optional_float(value: object) -> str:
    numeric_value = _optional_numeric_value(value)
    if numeric_value is None:
        return NA_TEXT
    return _format_numeric(float(numeric_value))


def _format_optional_int(value: object) -> str:
    int_value = _optional_int_value(value)
    if int_value is None:
        return NA_TEXT
    return str(int_value)


def _optional_numeric_value(value: object) -> float | None:
    if isinstance(value, Real) and not isinstance(value, bool):
        return float(value)
    return None


def _optional_int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _as_phase_cycle_rows(value: object) -> tuple[tuple[float, float], ...]:
    if not isinstance(value, list):
        return ()
    rows: list[tuple[float, float]] = []
    for row in value:
        if isinstance(row, list) and len(row) >= 2:
            rows.append((float(row[0]), float(row[1])))
    return tuple(rows)


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {}

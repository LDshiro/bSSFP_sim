"""Metadata viewer panel for the Chapter 7 GUI."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from bssfpviz.gui.adapters import coerce_loaded_dataset_view


class MetadataPanel(QWidget):
    """Read-only text panel that summarizes a loaded dataset."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._primary_view: Any | None = None
        self._compare_view: Any | None = None
        self._primary_path: Path | None = None
        self._compare_path: Path | None = None
        self._active_slot = "primary"
        self._compare_enabled = False
        layout = QVBoxLayout(self)
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setObjectName("metadata-text")
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)
        self.set_text("No dataset loaded.")

    def set_text(self, text: str) -> None:
        """Set the raw text shown by the panel."""
        self.text_edit.setPlainText(text)

    def set_dataset(self, dataset: Any, path: Path | None = None) -> None:
        """Render a formatted summary for the given dataset."""
        view = coerce_loaded_dataset_view(dataset, path=path)
        self.set_comparison_state(
            primary_dataset=view,
            primary_path=path or view.source_path,
            compare_dataset=None,
            compare_path=None,
            active_slot="primary",
            compare_enabled=False,
        )

    def set_comparison_state(
        self,
        *,
        primary_dataset: Any | None,
        primary_path: Path | None,
        compare_dataset: Any | None,
        compare_path: Path | None,
        active_slot: str,
        compare_enabled: bool,
    ) -> None:
        """Store comparison-aware dataset metadata and refresh the text output."""
        self._primary_view = (
            None
            if primary_dataset is None
            else coerce_loaded_dataset_view(primary_dataset, path=primary_path)
        )
        self._compare_view = (
            None
            if compare_dataset is None
            else coerce_loaded_dataset_view(compare_dataset, path=compare_path)
        )
        self._primary_path = primary_path
        self._compare_path = compare_path
        self._active_slot = active_slot
        self._compare_enabled = compare_enabled
        self.refresh()

    def refresh(self) -> None:
        """Refresh the metadata text from the stored comparison state."""
        if self._primary_view is None and self._compare_view is None:
            self.set_text("No dataset loaded.")
            return

        lines = [
            f"active_slot: {self._active_slot}",
            f"compare_enabled: {self._compare_enabled}",
            "",
        ]

        if self._primary_view is not None:
            lines.extend(_summary_lines("Primary", self._primary_view, self._primary_path))
            lines.append("")

        if self._compare_view is not None:
            lines.extend(_summary_lines("Compare", self._compare_view, self._compare_path))

        self.set_text("\n".join(lines).rstrip())


def _shape_text(value: object) -> str:
    shape = getattr(value, "shape", None)
    return str(shape) if shape is not None else "missing"


def _as_mapping(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _summary_lines(title: str, dataset: Any, path: Path | None) -> list[str]:
    view = coerce_loaded_dataset_view(dataset, path=path)
    meta = view.meta
    config = view.config
    physics = _as_mapping(config.get("physics", {}))
    sequence = _as_mapping(config.get("sequence", {}))
    sweep = _as_mapping(config.get("sweep", {}))
    return [
        f"{title}",
        f"  file_path: {path or view.source_path or ''}",
        f"  schema_version: {meta.get('schema_version', '')}",
        f"  created_at_utc: {meta.get('created_at_utc', '')}",
        f"  case_name: {meta.get('case_name', '')}",
        f"  app_version: {meta.get('app_version', '')}",
        "  Physics",
        f"    T1_s: {physics.get('T1_s', '')}",
        f"    T2_s: {physics.get('T2_s', '')}",
        f"    M0: {physics.get('M0', '')}",
        "  Sequence",
        f"    TR_s: {sequence.get('TR_s', '')}",
        f"    rf_duration_s: {sequence.get('rf_duration_s', '')}",
        f"    n_rf: {sequence.get('n_rf', '')}",
        f"    alpha_deg: {sequence.get('alpha_deg', '')}",
        f"    readout_fraction_of_free: {sequence.get('readout_fraction_of_free', '')}",
        "  Sweep",
        f"    delta_f_min_hz: {sweep.get('delta_f_min_hz', '')}",
        f"    delta_f_max_hz: {sweep.get('delta_f_max_hz', '')}",
        f"    delta_f_count: {sweep.get('delta_f_count', '')}",
        "  Shapes",
        f"    rk_magnetization: {_shape_text(view.rk_magnetization)}",
        f"    steady_state_orbit: {_shape_text(view.steady_state_orbit)}",
        f"    profiles_real: {_shape_text(view.profiles_complex_real)}",
        f"    profiles_sos: {_shape_text(view.profiles_sos)}",
    ]

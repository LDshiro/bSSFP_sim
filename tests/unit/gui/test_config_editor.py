"""Tests for the Chapter 5 config editor widget."""

from __future__ import annotations

import numpy as np
import pytest

from bssfpviz.gui.adapters import make_default_run_config
from bssfpviz.gui.config_editor import ConfigEditor


def test_config_editor_round_trips_default_config(qapp: object) -> None:
    _ = qapp
    editor = ConfigEditor()
    config = make_default_run_config()

    editor.set_config(config)
    round_trip = editor.get_config()

    assert round_trip.meta.case_name == config.meta.case_name
    assert round_trip.sequence.waveform_kind == config.sequence.waveform_kind
    assert round_trip.sequence.n_rf == config.sequence.n_rf
    np.testing.assert_allclose(round_trip.phase_cycles.values_deg, config.phase_cycles.values_deg)


def test_config_editor_phase_cycle_rows_can_be_added_and_removed(qapp: object) -> None:
    _ = qapp
    editor = ConfigEditor()

    initial_rows = editor.phase_cycle_table.rowCount()
    editor.add_acquisition_row()
    assert editor.phase_cycle_table.rowCount() == initial_rows + 1

    editor.remove_acquisition_row()
    assert editor.phase_cycle_table.rowCount() == initial_rows


def test_config_editor_rejects_invalid_rf_duration(qapp: object) -> None:
    _ = qapp
    editor = ConfigEditor()
    editor.tr_spin.setValue(0.004)
    editor.rf_duration_spin.setValue(0.004)

    with pytest.raises(ValueError, match="rf_duration_s"):
        editor.get_config()

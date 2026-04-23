"""Integration tests for the generic preview inspector shell."""

from __future__ import annotations

import time
from pathlib import Path
from textwrap import dedent

import pytest

pytest.importorskip("PySide6")

from bssfpviz.gui.generic_preview_window import GenericPreviewWindow
from bssfpviz.models.comparison import ExperimentConfig
from bssfpviz.workflows.compare import run_comparison


def test_generic_experiment_editor_round_trips_yaml(
    qapp: object,
    tmp_path: Path,
) -> None:
    _ = qapp
    input_path = tmp_path / "input.yaml"
    output_path = tmp_path / "output.yaml"
    input_path.write_text(_mixed_fastse_vfa_config_text(), encoding="utf-8")
    window = GenericPreviewWindow()

    window.load_config_from_path(input_path)
    saved_config = window.experiment_editor.save_yaml(output_path)
    loaded_config = ExperimentConfig.from_yaml(output_path)

    assert saved_config.to_mapping() == loaded_config.to_mapping()
    assert loaded_config.run_a.sequence_family.name == "FASTSE"
    assert loaded_config.run_b.sequence_family.name == "VFA_FSE"

    window.close()


def test_generic_preview_window_renders_fastse_timing_rows(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    tmp_path: Path,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    config_path = tmp_path / "generic_fastse.yaml"
    config_path.write_text(_fastse_preview_config_text(), encoding="utf-8")
    window = GenericPreviewWindow()

    window.load_config_from_path(config_path)
    qapp.processEvents()

    assert window.inspector_tabs.tabText(0) == "Sequence"
    assert window.timing_contrast_panel.get_run_value_text("run_a", "te_center_k_ms") != "N/A"
    assert window.timing_contrast_panel.get_run_value_text("run_a", "te_equiv_busse_ms") == "N/A"
    assert window.timing_contrast_panel.get_run_value_text("run_b", "ft_wh2006") != "N/A"
    assert window.timing_contrast_panel.get_run_value_text("run_b", "te_contrast_wh_ms") != "N/A"
    assert window.timing_contrast_panel.get_run_value_text("run_a", "tscan_s") == (
        "Not implemented in this phase"
    )
    assert window.timing_contrast_panel.get_delta_value_text("esp_ms") == "0.000"
    assert window.sequence_panel.get_run_table_cell_text("run_a", "primary", 0, 1) == "90.000"
    assert window.sequence_panel.get_run_table_cell_text("run_a", "primary", 0, 2) == "0.000"
    assert window.sequence_panel.get_run_table_cell_text("run_a", "secondary", 0, 1) == "8.000"
    assert window.sequence_panel.get_run_table_cell_text("run_a", "secondary", 0, 2) == "4.000"
    assert window.sequence_panel.get_run_summary_value_text("run_a", "esp_ms") == "8.000"
    assert window.sequence_panel.get_delta_value_text("esp_ms") == "0.000"
    assert "FASTSE preview uses the idealized hard-pulse baseline." in (
        window.timing_contrast_panel.run_a_warning_label.text()
    )

    window.close()


def test_generic_preview_window_renders_vfa_timing_rows_and_refreshes(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    tmp_path: Path,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    config_path = tmp_path / "generic_refresh.yaml"
    config_path.write_text(_fastse_preview_config_text(), encoding="utf-8")
    window = GenericPreviewWindow()

    window.load_config_from_path(config_path)
    qapp.processEvents()
    assert window.timing_contrast_panel.get_run_value_text("run_a", "te_equiv_busse_ms") == "N/A"

    vfa_path = tmp_path / "generic_vfa.yaml"
    vfa_path.write_text(_vfa_preview_config_text(), encoding="utf-8")
    window.experiment_editor.load_yaml(vfa_path)
    window.refresh_preview()
    qapp.processEvents()

    assert window.config_path_edit.text() == str(config_path)
    assert window.timing_contrast_panel.get_run_value_text("run_a", "te_equiv_busse_ms") != "N/A"
    assert window.timing_contrast_panel.get_run_value_text("run_a", "ft_wh2006") != "N/A"
    assert window.timing_contrast_panel.get_run_value_text("run_a", "te_contrast_wh_ms") != "N/A"
    assert window.timing_contrast_panel.get_run_value_text("run_a", "te_contrast_ms") != "N/A"
    assert window.timing_contrast_panel.get_delta_value_text("te_contrast_ms") != "N/A"
    assert window.sequence_panel.get_run_table_cell_text("run_a", "primary", 1, 1) == "180.000"
    assert window.sequence_panel.get_run_table_cell_text("run_b", "primary", 1, 1) == "150.000"
    assert window.sequence_panel.get_run_table_cell_text("run_b", "primary", 1, 2) == "90.000"
    assert window.sequence_panel.get_run_table_cell_text("run_a", "secondary", 0, 1) == "8.000"
    assert window.sequence_panel.get_run_table_cell_text("run_a", "secondary", 0, 2) == "4.000"
    assert window.sequence_panel.get_delta_value_text("sample_count_echo") == "0"
    assert "Busse contrast-equivalent TE is derived" in (
        window.timing_contrast_panel.run_a_warning_label.text()
    )
    assert window.last_refreshed_label.text().startswith("Last refreshed: ")

    window.close()


def test_generic_preview_window_runs_compare_and_auto_loads_bundle(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    tmp_path: Path,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    config_path = tmp_path / "generic_compare.yaml"
    output_path = tmp_path / "generic_compare.h5"
    config_path.write_text(_fastse_preview_config_text(), encoding="utf-8")
    window = GenericPreviewWindow()

    window.load_config_from_path(config_path)
    window.run_compare_to_path(output_path)
    _wait_for_compare(window, qapp)

    assert window.bundle_path_edit.text() == str(output_path)
    assert window.results_panel.get_run_summary_value_text("run_a", "echo_peak_abs") != "N/A"
    assert window.comparison_summary_panel.get_value_text(
        "matched_constraints",
        "delta_echo_peak_abs",
    ) != "N/A"
    assert window.scene_panel.frame_count() > 0
    assert "comparison finished" in window.log_panel.text_edit.toPlainText()

    window.close()


def test_generic_preview_window_rejects_existing_compare_output(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    tmp_path: Path,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    output_path = tmp_path / "existing.h5"
    output_path.write_text("already here", encoding="utf-8")
    window = GenericPreviewWindow()

    with pytest.raises(FileExistsError):
        window.run_compare_to_path(output_path)

    window.close()


def test_generic_preview_window_renders_bssfp_rows(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    tmp_path: Path,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    config_path = tmp_path / "generic_bssfp.yaml"
    config_path.write_text(_bssfp_preview_config_text(), encoding="utf-8")
    window = GenericPreviewWindow()

    window.load_config_from_path(config_path)
    qapp.processEvents()

    assert window.timing_contrast_panel.get_run_value_text("run_a", "tr_ms") == "4.000"
    assert window.timing_contrast_panel.get_run_value_text("run_a", "rf_duration_ms") == "1.000"
    assert window.timing_contrast_panel.get_run_value_text("run_a", "readout_time_ms") == "2.500"
    assert window.timing_contrast_panel.get_run_value_text("run_a", "te_center_k_ms") == "N/A"
    assert window.timing_contrast_panel.get_delta_value_text("te_center_k_ms") == "N/A"
    assert window.sequence_panel.get_run_table_cell_text("run_a", "primary", 0, 1) == "0.000"
    assert window.sequence_panel.get_run_table_cell_text("run_a", "primary", 1, 2) == "180.000"
    assert window.sequence_panel.get_run_summary_value_text("run_a", "tr_ms") == "4.000"
    assert window.sequence_panel.get_run_summary_value_text("run_a", "delta_f_count") == "3"
    assert window.sequence_panel.get_delta_value_text("tr_ms") == "0.000"

    window.close()


def test_generic_preview_window_loads_fastse_bundle_results(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    tmp_path: Path,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    bundle_path = _write_comparison_bundle(
        tmp_path,
        file_stem="fastse_bundle",
        config_text=_fastse_bundle_config_text(),
    )
    window = GenericPreviewWindow()

    window.load_bundle_from_path(bundle_path)
    qapp.processEvents()

    assert window.results_panel.get_run_summary_value_text("run_a", "echo_peak_abs") != "N/A"
    assert window.results_panel.get_run_curve_count("run_a", "primary") == 2
    assert window.results_panel.get_run_curve_count("run_a", "secondary") == 0
    assert window.comparison_summary_panel.get_value_text(
        "matched_constraints",
        "delta_echo_peak_abs",
    ) != "N/A"
    assert "comparison_bundle" in window.bundle_metadata_panel.text_edit.toPlainText()
    assert "Loaded comparison bundle" in window.log_panel.text_edit.toPlainText()

    window.close()


def test_generic_preview_window_loads_bssfp_bundle_results(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    tmp_path: Path,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    bundle_path = _write_comparison_bundle(
        tmp_path,
        file_stem="bssfp_bundle",
        config_text=_bssfp_bundle_config_text(),
    )
    window = GenericPreviewWindow()

    window.load_bundle_from_path(bundle_path)
    qapp.processEvents()

    assert window.results_panel.get_run_summary_value_text("run_a", "n_delta_f") == "3"
    assert window.results_panel.get_run_curve_count("run_a", "primary") == 1
    assert window.results_panel.get_run_curve_count("run_a", "secondary") == 2
    assert window.results_panel.get_delta_value_text("delta_sos_peak") != "N/A"
    assert window.scene_panel.frame_count() > 0

    window.close()


def test_generic_preview_window_bundle_mismatch_warning_and_clear(
    monkeypatch: pytest.MonkeyPatch,
    qapp: object,
    tmp_path: Path,
) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    preview_path = tmp_path / "preview_fastse.yaml"
    preview_path.write_text(_fastse_preview_config_text(), encoding="utf-8")
    bundle_path = _write_comparison_bundle(
        tmp_path,
        file_stem="bssfp_bundle_mismatch",
        config_text=_bssfp_bundle_config_text(),
    )
    window = GenericPreviewWindow()

    window.load_config_from_path(preview_path)
    window.load_bundle_from_path(bundle_path)
    qapp.processEvents()

    metadata_text = window.bundle_metadata_panel.text_edit.toPlainText()
    log_text = window.log_panel.text_edit.toPlainText()
    assert "Warnings" in metadata_text
    assert "does not match bundle family" in metadata_text
    assert "Source mismatch warning" in log_text

    window.clear_bundle()
    qapp.processEvents()

    assert "Load a comparison bundle" in window.bundle_metadata_panel.text_edit.toPlainText()
    assert "Load a comparison bundle" in window.results_panel.note_label.text()

    window.close()


def _fastse_preview_config_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_resolution

        common_physics:
          T1_s: 1.2
          T2_s: 0.08
          M0: 1.0

        run_a:
          sequence_family: FASTSE
          label: fastse_a
          fastse:
            case_name: fastse_a
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_const_deg: 180.0
            phi_ref_deg: 90.0
            etl: 4
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d

        run_b:
          sequence_family: FASTSE
          label: fastse_b
          fastse:
            case_name: fastse_b
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_const_deg: 120.0
            phi_ref_deg: 90.0
            etl: 4
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d
        """
    ).strip()


def _vfa_preview_config_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_TE_contrast

        common_physics:
          T1_s: 1.2
          T2_s: 0.08
          M0: 1.0

        run_a:
          sequence_family: VFA_FSE
          label: vfa_a
          vfa_fse:
            case_name: vfa_a
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_train_deg:
              - 180.0
              - 150.0
              - 120.0
              - 90.0
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d

        run_b:
          sequence_family: VFA_FSE
          label: vfa_b
          vfa_fse:
            case_name: vfa_b
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_train_deg:
              - 150.0
              - 130.0
              - 110.0
              - 90.0
            phi_ref_train_deg:
              - 90.0
              - 100.0
              - 110.0
              - 120.0
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d
        """
    ).strip()


def _bssfp_preview_config_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_resolution

        common_physics:
          T1_s: 1.5
          T2_s: 1.0
          M0: 1.0

        run_a:
          sequence_family: BSSFP
          label: compare_a
          bssfp:
            case_name: compare_a
            sequence:
              TR_s: 0.004
              rf_duration_s: 0.001
              n_rf: 8
              alpha_deg: 45.0
              waveform_kind: rect
              readout_fraction_of_free: 0.5
            phase_cycles:
              values_deg:
                - [0.0, 0.0]
                - [0.0, 180.0]
            sweep:
              delta_f_hz:
                start: -20.0
                stop: 20.0
                count: 3

        run_b:
          sequence_family: BSSFP
          label: compare_b
          bssfp:
            case_name: compare_b
            sequence:
              TR_s: 0.004
              rf_duration_s: 0.001
              n_rf: 8
              alpha_deg: 50.0
              waveform_kind: rect
              readout_fraction_of_free: 0.5
            phase_cycles:
              values_deg:
                - [0.0, 0.0]
                - [0.0, 180.0]
            sweep:
              delta_f_hz:
                start: -20.0
                stop: 20.0
                count: 3
        """
    ).strip()


def _mixed_fastse_vfa_config_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_TE_contrast

        common_physics:
          T1_s: 1.2
          T2_s: 0.08
          M0: 1.0

        run_a:
          sequence_family: FASTSE
          label: fastse_low
          fastse:
            case_name: fastse_low
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_const_deg: 120.0
            phi_ref_deg: 90.0
            etl: 4
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0

        run_b:
          sequence_family: VFA_FSE
          label: vfa_manual
          vfa_fse:
            case_name: vfa_manual
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_train_deg:
              - 150.0
              - 130.0
              - 110.0
              - 90.0
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
        """
    ).strip()


def _fastse_bundle_config_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_TE_contrast

        common_physics:
          T1_s: 1.2
          T2_s: 0.08
          M0: 1.0

        run_a:
          sequence_family: FASTSE
          label: fastse_a
          fastse:
            case_name: fastse_a
            description: left branch
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_const_deg: 180.0
            phi_ref_deg: 90.0
            etl: 4
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d

        run_b:
          sequence_family: FASTSE
          label: fastse_b
          fastse:
            case_name: fastse_b
            description: right branch
            alpha_exc_deg: 90.0
            phi_exc_deg: 0.0
            alpha_ref_const_deg: 120.0
            phi_ref_deg: 90.0
            etl: 4
            esp_ms: 8.0
            te_nominal_ms: 16.0
            n_iso: 101
            off_resonance_hz: 0.0
            timing_mode: user_fixed_ESP
            initial_state_mode: equilibrium
            dephasing_model: effective_1d
        """
    ).strip()


def _bssfp_bundle_config_text() -> str:
    return dedent(
        """
        comparison_scope: physics_only
        comparison_modes:
          - matched_resolution

        common_physics:
          T1_s: 1.5
          T2_s: 1.0
          M0: 1.0

        run_a:
          sequence_family: BSSFP
          label: compare_a
          bssfp:
            case_name: compare_a
            description: left branch
            sequence:
              TR_s: 0.004
              rf_duration_s: 0.001
              n_rf: 8
              alpha_deg: 45.0
              waveform_kind: rect
              readout_fraction_of_free: 0.5
            phase_cycles:
              values_deg:
                - [0.0, 0.0]
                - [0.0, 180.0]
            sweep:
              delta_f_hz:
                start: -20.0
                stop: 20.0
                count: 3
            integration:
              rk_method: PROPAGATOR
              rk_superperiods: 2
              rk_rtol: 1.0e-6
              rk_atol: 1.0e-8
              rk_max_step_s: 1.0e-4
              save_every_time_step: true

        run_b:
          sequence_family: BSSFP
          label: compare_b
          bssfp:
            case_name: compare_b
            description: right branch
            sequence:
              TR_s: 0.004
              rf_duration_s: 0.001
              n_rf: 8
              alpha_deg: 50.0
              waveform_kind: rect
              readout_fraction_of_free: 0.5
            phase_cycles:
              values_deg:
                - [0.0, 0.0]
                - [0.0, 180.0]
            sweep:
              delta_f_hz:
                start: -20.0
                stop: 20.0
                count: 3
            integration:
              rk_method: RK45
              rk_superperiods: 2
              rk_rtol: 1.0e-6
              rk_atol: 1.0e-8
              rk_max_step_s: 1.0e-4
              save_every_time_step: true
        """
    ).strip()


def _write_comparison_bundle(tmp_path: Path, *, file_stem: str, config_text: str) -> Path:
    config_path = tmp_path / f"{file_stem}.yaml"
    output_path = tmp_path / f"{file_stem}.h5"
    config_path.write_text(config_text, encoding="utf-8")
    config = ExperimentConfig.from_yaml(config_path)
    _ = run_comparison(config, output_path)
    return output_path


def _wait_for_compare(window: GenericPreviewWindow, qapp: object) -> None:
    deadline = time.monotonic() + 10.0
    while window._compare_thread is not None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()
    assert window._compare_thread is None

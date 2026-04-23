"""Tests for generic animation view-models and playback state."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from bssfpviz.gui.animation_view_model import AnimationViewModel
from bssfpviz.gui.generic_playback_controller import GenericPlaybackController
from bssfpviz.models.comparison import CommonPhysicsConfig, FastSEFamilyConfig
from bssfpviz.sequences.fastse.runner import run_fastse_simulation


def test_animation_view_model_from_fastse_result() -> None:
    config = FastSEFamilyConfig(
        case_name="fastse_anim",
        description="animation smoke",
        alpha_exc_deg=90.0,
        phi_exc_deg=0.0,
        alpha_ref_const_deg=120.0,
        phi_ref_deg=90.0,
        etl=3,
        esp_ms=8.0,
        te_nominal_ms=None,
        n_iso=7,
        off_resonance_hz=0.0,
    )
    result = run_fastse_simulation(
        config,
        CommonPhysicsConfig(t1_s=1.2, t2_s=0.08, m0=1.0),
        run_label="fastse",
    )

    model = AnimationViewModel.from_simulation_result(result)

    assert model.n_acq == 1
    assert model.n_spins == 7
    assert model.get_frame_count("reference") == 7
    assert model.get_vectors_xyz("reference", 0, 0).shape == (7, 3)
    assert model.get_steady_orbit_xyz(0).shape == (7, 7, 3)


def test_generic_playback_controller_updates_frame(
    qapp: object,
) -> None:
    _ = qapp
    config = FastSEFamilyConfig(
        case_name="fastse_controller",
        description="controller smoke",
        alpha_exc_deg=90.0,
        phi_exc_deg=0.0,
        alpha_ref_const_deg=180.0,
        phi_ref_deg=90.0,
        etl=2,
        esp_ms=8.0,
        te_nominal_ms=None,
        n_iso=5,
        off_resonance_hz=0.0,
    )
    result = run_fastse_simulation(
        config,
        CommonPhysicsConfig(t1_s=1.2, t2_s=0.08, m0=1.0),
        run_label="fastse",
    )
    model = AnimationViewModel.from_simulation_result(result)
    controller = GenericPlaybackController()

    controller.set_view_model(model)
    controller.set_frame_index(2)

    assert controller.state().frame_index == 2
    assert controller.view_model() is model

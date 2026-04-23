"""Manual VFA-FSE family runner for the comparison backend."""

from __future__ import annotations

from bssfpviz.models.comparison import (
    CommonPhysicsConfig,
    SequenceFamily,
    SimulationResult,
    VFAFSEFamilyConfig,
)
from bssfpviz.sequences.fse_common import run_train_based_fse_simulation
from bssfpviz.sequences.fse_contrast import (
    compute_busse_te_ms_per_echo,
    compute_wh2006_metrics,
    run_no_relaxation_reference,
)


def run_vfa_fse_simulation(
    config: VFAFSEFamilyConfig,
    physics: CommonPhysicsConfig,
    *,
    run_label: str = "vfa_fse",
) -> SimulationResult:
    """Run the idealized manual VFA-FSE baseline and return a generic result."""
    if config.phi_ref_train_deg is None:
        msg = "phi_ref_train_deg must be resolved before running VFA_FSE_MANUAL."
        raise ValueError(msg)
    phi_ref_train_deg = config.phi_ref_train_deg
    result = run_train_based_fse_simulation(
        sequence_family=SequenceFamily.VFA_FSE,
        run_label=run_label,
        case_name=config.case_name,
        description=config.description,
        physics=physics,
        alpha_exc_deg=config.alpha_exc_deg,
        phi_exc_deg=config.phi_exc_deg,
        alpha_ref_train_deg=config.alpha_ref_train_deg,
        phi_ref_train_deg=phi_ref_train_deg,
        esp_ms=config.esp_ms,
        n_iso=config.n_iso,
        off_resonance_hz=config.off_resonance_hz,
        metadata={"runner": "vfa_fse_family_runner"},
        family_metadata={
            "sequence_variant": config.sequence_variant,
            "phase_convention": "manual_ref_phase_train",
            "timing_mode": config.timing_mode,
            "initial_state_mode": config.initial_state_mode,
            "dephasing_model": config.dephasing_model,
        },
    )
    no_relaxation_result = run_no_relaxation_reference(
        sequence_family=SequenceFamily.VFA_FSE,
        run_label=run_label,
        case_name=config.case_name,
        description=config.description,
        physics=physics,
        alpha_exc_deg=config.alpha_exc_deg,
        phi_exc_deg=config.phi_exc_deg,
        alpha_ref_train_deg=config.alpha_ref_train_deg,
        phi_ref_train_deg=phi_ref_train_deg,
        esp_ms=config.esp_ms,
        n_iso=config.n_iso,
        off_resonance_hz=config.off_resonance_hz,
        metadata={"runner": "vfa_fse_family_runner_no_relax"},
        family_metadata={
            "sequence_variant": config.sequence_variant,
            "phase_convention": "manual_ref_phase_train",
            "timing_mode": config.timing_mode,
            "initial_state_mode": config.initial_state_mode,
            "dephasing_model": config.dephasing_model,
        },
    )
    te_equiv_busse_ms_per_echo = compute_busse_te_ms_per_echo(
        result,
        no_relaxation_result,
        t2_s=physics.t2_s,
    )
    wh_metrics = compute_wh2006_metrics(result, no_relaxation_result, physics=physics)
    center_echo_index = int(config.etl // 2)
    result.observables["te_equiv_busse_ms_per_echo"] = te_equiv_busse_ms_per_echo
    result.observables["ft_wh2006_per_echo"] = wh_metrics.ft_per_echo
    result.observables["te_contrast_wh_ms_per_echo"] = wh_metrics.te_contrast_wh_ms_per_echo
    result.scalars["te_equiv_busse_ms"] = float(te_equiv_busse_ms_per_echo[center_echo_index])
    result.scalars["ft_wh2006"] = wh_metrics.ft_center_k
    result.scalars["te_contrast_wh_ms"] = wh_metrics.te_contrast_wh_ms
    result.scalars["te_contrast_ms"] = float(te_equiv_busse_ms_per_echo[center_echo_index])
    result.family_metadata["te_contrast_definition"] = "Busse"
    result.family_metadata["contrast_warnings"] = list(wh_metrics.warnings)
    return result

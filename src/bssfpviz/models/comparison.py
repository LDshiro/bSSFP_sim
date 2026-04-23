"""Generic comparison-oriented models for MRI sequence families."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import yaml

from bssfpviz.models.run_config import (
    IntegrationConfig,
    MetaConfig,
    OutputConfig,
    PhaseCycleConfig,
    RunConfig,
    SequenceConfig,
    SweepConfig,
)
from bssfpviz.models.run_config import (
    PhysicsConfig as RunPhysicsConfig,
)

FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]
ScalarValue = float | int | str | bool
SUPPORTED_COMPARISON_SCOPES = frozenset({"physics_only", "protocol_realistic"})
SUPPORTED_COMPARISON_MODES = frozenset(
    {
        "matched_TE_contrast",
        "matched_scan_time",
        "matched_SAR",
        "matched_voxel",
        "matched_resolution",
        "matched_coverage",
    }
)
SUPPORTED_FASTSE_COMPARISON_MODES = frozenset(
    {
        "matched_TE_contrast",
        "matched_resolution",
        "matched_voxel",
    }
)
SUPPORTED_VFA_FSE_COMPARISON_MODES = frozenset(
    {
        "matched_TE_contrast",
        "matched_resolution",
        "matched_voxel",
    }
)
SUPPORTED_FASTSE_VARIANTS = frozenset({"FASTSE_CONST"})
SUPPORTED_FASTSE_TIMING_MODES = frozenset({"user_fixed_ESP"})
SUPPORTED_FASTSE_INITIAL_STATE_MODES = frozenset({"equilibrium"})
SUPPORTED_FASTSE_DEPHASING_MODELS = frozenset({"effective_1d"})
SUPPORTED_VFA_FSE_VARIANTS = frozenset({"VFA_FSE_MANUAL"})


class SequenceFamily(StrEnum):
    """Supported MRI sequence families for the comparison backend."""

    BSSFP = "BSSFP"
    FASTSE = "FASTSE"
    VFA_FSE = "VFA_FSE"


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    msg = "Expected a mapping-compatible value."
    raise TypeError(msg)


def _optional_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    return _mapping(value)


def _require_key(mapping: dict[str, Any], key: str) -> Any:
    value = mapping.get(key)
    if value is None:
        msg = f"Missing required key: {key}"
        raise ValueError(msg)
    return value


def _as_axis_array(value: object, name: str) -> FloatArray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 1 or array.shape[0] == 0:
        msg = f"{name} must be a non-empty 1D float array."
        raise ValueError(msg)
    return np.array(array, dtype=np.float64, copy=True)


def _as_numeric_array(value: object, name: str) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim == 0:
        msg = f"{name} must be at least 1D."
        raise ValueError(msg)
    if np.issubdtype(array.dtype, np.complexfloating):
        return np.array(array, dtype=np.complex128, copy=True)
    if np.issubdtype(array.dtype, np.number) or np.issubdtype(array.dtype, np.bool_):
        return np.array(array, dtype=np.float64, copy=True)
    msg = f"{name} must be numeric."
    raise ValueError(msg)


def _scalar_value(value: Any, *, name: str) -> ScalarValue:
    if isinstance(value, (bool, str, int, float)):
        return value
    if isinstance(value, np.generic):
        item = value.item()
        if isinstance(item, (bool, str, int, float)):
            return item
    msg = f"{name} must be a scalar string/bool/int/float value."
    raise ValueError(msg)


@dataclass(slots=True)
class CommonPhysicsConfig:
    """Shared physics inputs for comparison experiments."""

    t1_s: float
    t2_s: float
    m0: float

    def __post_init__(self) -> None:
        if self.t1_s <= 0.0 or self.t2_s <= 0.0:
            msg = "T1_s and T2_s must be positive."
            raise ValueError(msg)
        if self.m0 <= 0.0:
            msg = "M0 must be positive."
            raise ValueError(msg)

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> CommonPhysicsConfig:
        return cls(
            t1_s=float(_require_key(mapping, "T1_s")),
            t2_s=float(_require_key(mapping, "T2_s")),
            m0=float(_require_key(mapping, "M0")),
        )

    def to_run_physics(self) -> RunPhysicsConfig:
        """Return the legacy bSSFP CLI physics model."""
        return RunPhysicsConfig(t1_s=self.t1_s, t2_s=self.t2_s, m0=self.m0)

    def to_mapping(self) -> dict[str, float]:
        """Return a YAML-compatible mapping."""
        return {
            "T1_s": float(self.t1_s),
            "T2_s": float(self.t2_s),
            "M0": float(self.m0),
        }


@dataclass(slots=True)
class BSSFPFamilyConfig:
    """Family-specific settings for the current bSSFP implementation."""

    case_name: str
    description: str
    sequence: SequenceConfig
    phase_cycles: PhaseCycleConfig
    sweep: SweepConfig
    integration: IntegrationConfig = field(default_factory=IntegrationConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def __post_init__(self) -> None:
        if not self.case_name:
            msg = "case_name must not be empty."
            raise ValueError(msg)

    @classmethod
    def from_mapping(
        cls,
        mapping: dict[str, Any],
        *,
        default_case_name: str,
    ) -> BSSFPFamilyConfig:
        sequence_values = _mapping(_require_key(mapping, "sequence"))
        phase_values = _mapping(_require_key(mapping, "phase_cycles"))
        sweep_values = _mapping(_require_key(mapping, "sweep"))
        delta_f_values = _mapping(_require_key(sweep_values, "delta_f_hz"))
        integration_values = _optional_mapping(mapping.get("integration"))
        output_values = _optional_mapping(mapping.get("output"))
        return cls(
            case_name=str(mapping.get("case_name", default_case_name)),
            description=str(mapping.get("description", "")),
            sequence=SequenceConfig(
                tr_s=float(_require_key(sequence_values, "TR_s")),
                rf_duration_s=float(_require_key(sequence_values, "rf_duration_s")),
                n_rf=int(_require_key(sequence_values, "n_rf")),
                alpha_deg=float(_require_key(sequence_values, "alpha_deg")),
                waveform_kind=str(_require_key(sequence_values, "waveform_kind")),
                readout_fraction_of_free=float(
                    sequence_values.get("readout_fraction_of_free", 0.5)
                ),
            ),
            phase_cycles=PhaseCycleConfig(values_deg=_require_key(phase_values, "values_deg")),
            sweep=SweepConfig(
                start_hz=float(_require_key(delta_f_values, "start")),
                stop_hz=float(_require_key(delta_f_values, "stop")),
                count=int(_require_key(delta_f_values, "count")),
            ),
            integration=IntegrationConfig(
                rk_method=str(integration_values.get("rk_method", "PROPAGATOR")),
                rk_rtol=float(integration_values.get("rk_rtol", 1.0e-7)),
                rk_atol=float(integration_values.get("rk_atol", 1.0e-9)),
                rk_max_step_s=float(integration_values.get("rk_max_step_s", 5.0e-6)),
                rk_superperiods=int(integration_values.get("rk_superperiods", 60)),
                save_every_time_step=bool(integration_values.get("save_every_time_step", True)),
            ),
            output=OutputConfig(
                save_profiles=bool(output_values.get("save_profiles", True)),
                save_rk_trajectories=bool(output_values.get("save_rk_trajectories", True)),
                save_steady_state_orbit=bool(output_values.get("save_steady_state_orbit", True)),
                save_fixed_points=bool(output_values.get("save_fixed_points", True)),
            ),
        )

    def to_run_config(self, physics: CommonPhysicsConfig) -> RunConfig:
        """Build the legacy bSSFP RunConfig for execution."""
        return RunConfig(
            meta=MetaConfig(case_name=self.case_name, description=self.description),
            physics=physics.to_run_physics(),
            sequence=self.sequence,
            phase_cycles=self.phase_cycles,
            sweep=self.sweep,
            integration=self.integration,
            output=self.output,
        )

    def to_mapping(self) -> dict[str, Any]:
        """Return a YAML-compatible BSSFP branch mapping."""
        return {
            "case_name": self.case_name,
            "description": self.description,
            "sequence": {
                "TR_s": float(self.sequence.tr_s),
                "rf_duration_s": float(self.sequence.rf_duration_s),
                "n_rf": int(self.sequence.n_rf),
                "alpha_deg": float(self.sequence.alpha_deg),
                "waveform_kind": self.sequence.waveform_kind,
                "readout_fraction_of_free": float(self.sequence.readout_fraction_of_free),
            },
            "phase_cycles": {
                "values_deg": np.asarray(self.phase_cycles.values_deg, dtype=np.float64).tolist()
            },
            "sweep": {
                "delta_f_hz": {
                    "start": float(self.sweep.start_hz),
                    "stop": float(self.sweep.stop_hz),
                    "count": int(self.sweep.count),
                }
            },
            "integration": {
                "rk_method": self.integration.rk_method,
                "rk_rtol": float(self.integration.rk_rtol),
                "rk_atol": float(self.integration.rk_atol),
                "rk_max_step_s": float(self.integration.rk_max_step_s),
                "rk_superperiods": int(self.integration.rk_superperiods),
                "save_every_time_step": bool(self.integration.save_every_time_step),
            },
            "output": {
                "save_profiles": bool(self.output.save_profiles),
                "save_rk_trajectories": bool(self.output.save_rk_trajectories),
                "save_steady_state_orbit": bool(self.output.save_steady_state_orbit),
                "save_fixed_points": bool(self.output.save_fixed_points),
            },
        }


@dataclass(slots=True)
class FastSEFamilyConfig:
    """Family-specific settings for the initial idealized Fast SE implementation."""

    case_name: str
    description: str
    alpha_exc_deg: float
    phi_exc_deg: float
    alpha_ref_const_deg: float
    phi_ref_deg: float
    etl: int
    esp_ms: float
    te_nominal_ms: float | None
    n_iso: int
    off_resonance_hz: float
    sequence_variant: str = "FASTSE_CONST"
    timing_mode: str = "user_fixed_ESP"
    initial_state_mode: str = "equilibrium"
    dephasing_model: str = "effective_1d"

    def __post_init__(self) -> None:
        if not self.case_name:
            msg = "case_name must not be empty."
            raise ValueError(msg)
        if self.sequence_variant not in SUPPORTED_FASTSE_VARIANTS:
            msg = f"sequence_variant must be one of {sorted(SUPPORTED_FASTSE_VARIANTS)}."
            raise ValueError(msg)
        if self.timing_mode not in SUPPORTED_FASTSE_TIMING_MODES:
            msg = f"timing_mode must be one of {sorted(SUPPORTED_FASTSE_TIMING_MODES)}."
            raise ValueError(msg)
        if self.initial_state_mode not in SUPPORTED_FASTSE_INITIAL_STATE_MODES:
            msg = (
                "initial_state_mode must be one of "
                f"{sorted(SUPPORTED_FASTSE_INITIAL_STATE_MODES)}."
            )
            raise ValueError(msg)
        if self.dephasing_model not in SUPPORTED_FASTSE_DEPHASING_MODELS:
            msg = (
                "dephasing_model must be one of "
                f"{sorted(SUPPORTED_FASTSE_DEPHASING_MODELS)}."
            )
            raise ValueError(msg)
        if self.alpha_exc_deg <= 0.0 or self.alpha_ref_const_deg <= 0.0:
            msg = "alpha_exc_deg and alpha_ref_const_deg must be positive."
            raise ValueError(msg)
        if self.etl <= 0:
            msg = "etl must be positive."
            raise ValueError(msg)
        if self.esp_ms <= 0.0:
            msg = "esp_ms must be positive."
            raise ValueError(msg)
        if self.te_nominal_ms is not None and self.te_nominal_ms <= 0.0:
            msg = "te_nominal_ms must be positive when provided."
            raise ValueError(msg)
        if self.n_iso <= 0:
            msg = "n_iso must be positive."
            raise ValueError(msg)

    @classmethod
    def from_mapping(
        cls,
        mapping: dict[str, Any],
        *,
        default_case_name: str,
    ) -> FastSEFamilyConfig:
        return cls(
            case_name=str(mapping.get("case_name", default_case_name)),
            description=str(mapping.get("description", "")),
            alpha_exc_deg=float(_require_key(mapping, "alpha_exc_deg")),
            phi_exc_deg=float(mapping.get("phi_exc_deg", 0.0)),
            alpha_ref_const_deg=float(_require_key(mapping, "alpha_ref_const_deg")),
            phi_ref_deg=float(mapping.get("phi_ref_deg", 90.0)),
            etl=int(_require_key(mapping, "etl")),
            esp_ms=float(_require_key(mapping, "esp_ms")),
            te_nominal_ms=(
                None if mapping.get("te_nominal_ms") is None else float(mapping["te_nominal_ms"])
            ),
            n_iso=int(_require_key(mapping, "n_iso")),
            off_resonance_hz=float(mapping.get("off_resonance_hz", 0.0)),
            sequence_variant=str(mapping.get("sequence_variant", "FASTSE_CONST")),
            timing_mode=str(mapping.get("timing_mode", "user_fixed_ESP")),
            initial_state_mode=str(mapping.get("initial_state_mode", "equilibrium")),
            dephasing_model=str(mapping.get("dephasing_model", "effective_1d")),
        )

    def to_mapping(self) -> dict[str, Any]:
        """Return a YAML-compatible FASTSE branch mapping."""
        return {
            "case_name": self.case_name,
            "description": self.description,
            "alpha_exc_deg": float(self.alpha_exc_deg),
            "phi_exc_deg": float(self.phi_exc_deg),
            "alpha_ref_const_deg": float(self.alpha_ref_const_deg),
            "phi_ref_deg": float(self.phi_ref_deg),
            "etl": int(self.etl),
            "esp_ms": float(self.esp_ms),
            "te_nominal_ms": None
            if self.te_nominal_ms is None
            else float(self.te_nominal_ms),
            "n_iso": int(self.n_iso),
            "off_resonance_hz": float(self.off_resonance_hz),
            "sequence_variant": self.sequence_variant,
            "timing_mode": self.timing_mode,
            "initial_state_mode": self.initial_state_mode,
            "dephasing_model": self.dephasing_model,
        }


@dataclass(slots=True)
class VFAFSEFamilyConfig:
    """Family-specific settings for manual VFA-FSE train import."""

    case_name: str
    description: str
    alpha_exc_deg: float
    phi_exc_deg: float
    alpha_ref_train_deg: FloatArray
    phi_ref_train_deg: FloatArray | None
    esp_ms: float
    te_nominal_ms: float | None
    n_iso: int
    off_resonance_hz: float
    sequence_variant: str = "VFA_FSE_MANUAL"
    timing_mode: str = "user_fixed_ESP"
    initial_state_mode: str = "equilibrium"
    dephasing_model: str = "effective_1d"

    def __post_init__(self) -> None:
        if not self.case_name:
            msg = "case_name must not be empty."
            raise ValueError(msg)
        if self.sequence_variant not in SUPPORTED_VFA_FSE_VARIANTS:
            msg = f"sequence_variant must be one of {sorted(SUPPORTED_VFA_FSE_VARIANTS)}."
            raise ValueError(msg)
        if self.timing_mode not in SUPPORTED_FASTSE_TIMING_MODES:
            msg = f"timing_mode must be one of {sorted(SUPPORTED_FASTSE_TIMING_MODES)}."
            raise ValueError(msg)
        if self.initial_state_mode not in SUPPORTED_FASTSE_INITIAL_STATE_MODES:
            msg = (
                "initial_state_mode must be one of "
                f"{sorted(SUPPORTED_FASTSE_INITIAL_STATE_MODES)}."
            )
            raise ValueError(msg)
        if self.dephasing_model not in SUPPORTED_FASTSE_DEPHASING_MODELS:
            msg = (
                "dephasing_model must be one of "
                f"{sorted(SUPPORTED_FASTSE_DEPHASING_MODELS)}."
            )
            raise ValueError(msg)
        if self.alpha_exc_deg <= 0.0:
            msg = "alpha_exc_deg must be positive."
            raise ValueError(msg)
        self.alpha_ref_train_deg = _as_axis_array(self.alpha_ref_train_deg, "alpha_ref_train_deg")
        if np.any(self.alpha_ref_train_deg <= 0.0):
            msg = "alpha_ref_train_deg must contain positive values only."
            raise ValueError(msg)
        if self.phi_ref_train_deg is None:
            self.phi_ref_train_deg = np.full(self.alpha_ref_train_deg.shape, 90.0, dtype=np.float64)
        else:
            self.phi_ref_train_deg = _as_axis_array(self.phi_ref_train_deg, "phi_ref_train_deg")
        if self.alpha_ref_train_deg.shape != self.phi_ref_train_deg.shape:
            msg = "alpha_ref_train_deg and phi_ref_train_deg must have the same shape."
            raise ValueError(msg)
        if self.esp_ms <= 0.0:
            msg = "esp_ms must be positive."
            raise ValueError(msg)
        if self.te_nominal_ms is not None and self.te_nominal_ms <= 0.0:
            msg = "te_nominal_ms must be positive when provided."
            raise ValueError(msg)
        if self.n_iso <= 0:
            msg = "n_iso must be positive."
            raise ValueError(msg)

    @property
    def etl(self) -> int:
        """Return the echo-train length implied by the imported flip train."""
        return int(self.alpha_ref_train_deg.shape[0])

    @classmethod
    def from_mapping(
        cls,
        mapping: dict[str, Any],
        *,
        default_case_name: str,
    ) -> VFAFSEFamilyConfig:
        raw_phi_ref_train = mapping.get("phi_ref_train_deg")
        return cls(
            case_name=str(mapping.get("case_name", default_case_name)),
            description=str(mapping.get("description", "")),
            alpha_exc_deg=float(_require_key(mapping, "alpha_exc_deg")),
            phi_exc_deg=float(mapping.get("phi_exc_deg", 0.0)),
            alpha_ref_train_deg=_require_key(mapping, "alpha_ref_train_deg"),
            phi_ref_train_deg=raw_phi_ref_train,
            esp_ms=float(_require_key(mapping, "esp_ms")),
            te_nominal_ms=(
                None if mapping.get("te_nominal_ms") is None else float(mapping["te_nominal_ms"])
            ),
            n_iso=int(_require_key(mapping, "n_iso")),
            off_resonance_hz=float(mapping.get("off_resonance_hz", 0.0)),
            sequence_variant=str(mapping.get("sequence_variant", "VFA_FSE_MANUAL")),
            timing_mode=str(mapping.get("timing_mode", "user_fixed_ESP")),
            initial_state_mode=str(mapping.get("initial_state_mode", "equilibrium")),
            dephasing_model=str(mapping.get("dephasing_model", "effective_1d")),
        )

    def to_mapping(self) -> dict[str, Any]:
        """Return a YAML-compatible VFA-FSE branch mapping."""
        assert self.phi_ref_train_deg is not None
        return {
            "case_name": self.case_name,
            "description": self.description,
            "alpha_exc_deg": float(self.alpha_exc_deg),
            "phi_exc_deg": float(self.phi_exc_deg),
            "alpha_ref_train_deg": np.asarray(
                self.alpha_ref_train_deg, dtype=np.float64
            ).tolist(),
            "phi_ref_train_deg": np.asarray(self.phi_ref_train_deg, dtype=np.float64).tolist(),
            "esp_ms": float(self.esp_ms),
            "te_nominal_ms": None
            if self.te_nominal_ms is None
            else float(self.te_nominal_ms),
            "n_iso": int(self.n_iso),
            "off_resonance_hz": float(self.off_resonance_hz),
            "sequence_variant": self.sequence_variant,
            "timing_mode": self.timing_mode,
            "initial_state_mode": self.initial_state_mode,
            "dephasing_model": self.dephasing_model,
        }


@dataclass(slots=True)
class ExperimentRunConfig:
    """One sequence-family branch inside a comparison experiment."""

    sequence_family: SequenceFamily
    label: str
    bssfp: BSSFPFamilyConfig | None = None
    fastse: FastSEFamilyConfig | None = None
    vfa_fse: VFAFSEFamilyConfig | None = None

    def __post_init__(self) -> None:
        if not self.label:
            msg = "label must not be empty."
            raise ValueError(msg)
        if self.sequence_family == SequenceFamily.BSSFP and self.bssfp is None:
            msg = "bssfp configuration is required when sequence_family is BSSFP."
            raise ValueError(msg)
        if self.sequence_family == SequenceFamily.FASTSE and self.fastse is None:
            msg = "fastse configuration is required when sequence_family is FASTSE."
            raise ValueError(msg)
        if self.sequence_family == SequenceFamily.VFA_FSE and self.vfa_fse is None:
            msg = "vfa_fse configuration is required when sequence_family is VFA_FSE."
            raise ValueError(msg)
        if self.sequence_family != SequenceFamily.BSSFP and self.bssfp is not None:
            msg = "bssfp settings may only be supplied for the BSSFP family."
            raise ValueError(msg)
        if self.sequence_family != SequenceFamily.FASTSE and self.fastse is not None:
            msg = "fastse settings may only be supplied for the FASTSE family."
            raise ValueError(msg)
        if self.sequence_family != SequenceFamily.VFA_FSE and self.vfa_fse is not None:
            msg = "vfa_fse settings may only be supplied for the VFA_FSE family."
            raise ValueError(msg)

    @classmethod
    def from_mapping(
        cls,
        mapping: dict[str, Any],
        *,
        default_label: str,
    ) -> ExperimentRunConfig:
        family = SequenceFamily(str(_require_key(mapping, "sequence_family")).strip().upper())
        label = str(mapping.get("label", default_label))
        bssfp_mapping = _optional_mapping(mapping.get("bssfp")) if "bssfp" in mapping else {}
        fastse_mapping = _optional_mapping(mapping.get("fastse")) if "fastse" in mapping else {}
        vfa_fse_mapping = _optional_mapping(mapping.get("vfa_fse")) if "vfa_fse" in mapping else {}
        return cls(
            sequence_family=family,
            label=label,
            bssfp=(
                BSSFPFamilyConfig.from_mapping(bssfp_mapping, default_case_name=label)
                if family == SequenceFamily.BSSFP
                else None
            ),
            fastse=(
                FastSEFamilyConfig.from_mapping(fastse_mapping, default_case_name=label)
                if family == SequenceFamily.FASTSE
                else None
            ),
            vfa_fse=(
                VFAFSEFamilyConfig.from_mapping(vfa_fse_mapping, default_case_name=label)
                if family == SequenceFamily.VFA_FSE
                else None
            ),
        )

    def to_run_config(self, physics: CommonPhysicsConfig) -> RunConfig:
        """Return a legacy bSSFP run config when supported."""
        if self.sequence_family != SequenceFamily.BSSFP or self.bssfp is None:
            msg = f"Sequence family {self.sequence_family.value} is not implemented yet."
            raise ValueError(msg)
        return self.bssfp.to_run_config(physics)

    def to_mapping(self) -> dict[str, Any]:
        """Return a YAML-compatible run branch mapping."""
        values: dict[str, Any] = {
            "sequence_family": self.sequence_family.value,
            "label": self.label,
        }
        if self.sequence_family == SequenceFamily.BSSFP and self.bssfp is not None:
            values["bssfp"] = self.bssfp.to_mapping()
        elif self.sequence_family == SequenceFamily.FASTSE and self.fastse is not None:
            values["fastse"] = self.fastse.to_mapping()
        elif self.sequence_family == SequenceFamily.VFA_FSE and self.vfa_fse is not None:
            values["vfa_fse"] = self.vfa_fse.to_mapping()
        return values


@dataclass(slots=True)
class ExperimentOutputConfig:
    """Optional output-side settings for comparison experiments."""

    summary_json: str | None = None

    def to_mapping(self) -> dict[str, str]:
        """Return a YAML-compatible output mapping."""
        if self.summary_json is None:
            return {}
        return {"summary_json": self.summary_json}


@dataclass(slots=True)
class CompiledSequence:
    """Generic event-train representation used by family runners."""

    sequence_family: SequenceFamily
    label: str
    event_dt_s: FloatArray
    event_ux: FloatArray
    event_uy: FloatArray
    sample_times_s: dict[str, FloatArray] = field(default_factory=dict)
    family_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.event_dt_s = _as_axis_array(self.event_dt_s, "event_dt_s")
        self.event_ux = _as_axis_array(self.event_ux, "event_ux")
        self.event_uy = _as_axis_array(self.event_uy, "event_uy")
        if not (self.event_dt_s.shape == self.event_ux.shape == self.event_uy.shape):
            msg = "event_dt_s, event_ux, and event_uy must have the same shape."
            raise ValueError(msg)
        self.sample_times_s = {
            str(key): _as_axis_array(value, f"sample_times_s[{key!r}]")
            for key, value in self.sample_times_s.items()
        }
        self.family_metadata = {str(key): value for key, value in self.family_metadata.items()}


@dataclass(slots=True)
class SimulationResult:
    """Generic family-agnostic sequence result container."""

    sequence_family: SequenceFamily
    run_label: str
    case_name: str
    description: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    family_metadata: dict[str, Any] = field(default_factory=dict)
    axes: dict[str, FloatArray] = field(default_factory=dict)
    trajectories: dict[str, np.ndarray] = field(default_factory=dict)
    observables: dict[str, np.ndarray] = field(default_factory=dict)
    scalars: dict[str, ScalarValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_label:
            msg = "run_label must not be empty."
            raise ValueError(msg)
        if not self.case_name:
            msg = "case_name must not be empty."
            raise ValueError(msg)
        self.metadata = {str(key): str(value) for key, value in self.metadata.items()}
        self.family_metadata = {str(key): value for key, value in self.family_metadata.items()}
        self.axes = {
            str(key): _as_axis_array(value, f"axes[{key!r}]") for key, value in self.axes.items()
        }
        self.trajectories = {
            str(key): _as_numeric_array(value, f"trajectories[{key!r}]")
            for key, value in self.trajectories.items()
        }
        self.observables = {
            str(key): _as_numeric_array(value, f"observables[{key!r}]")
            for key, value in self.observables.items()
        }
        self.scalars = {
            str(key): _scalar_value(value, name=f"scalars[{key!r}]")
            for key, value in self.scalars.items()
        }


@dataclass(slots=True)
class ComparisonBundle:
    """Generic pairwise comparison output."""

    comparison_scope: str
    comparison_modes: tuple[str, ...]
    run_a: SimulationResult
    run_b: SimulationResult
    matched_constraints_summary: dict[str, ScalarValue] = field(default_factory=dict)
    derived_ratios: dict[str, float] = field(default_factory=dict)
    report_metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.comparison_scope not in SUPPORTED_COMPARISON_SCOPES:
            msg = (
                "comparison_scope must be one of "
                f"{sorted(SUPPORTED_COMPARISON_SCOPES)}."
            )
            raise ValueError(msg)
        if len(self.comparison_modes) == 0:
            msg = "comparison_modes must contain at least one entry."
            raise ValueError(msg)
        invalid_modes = [
            mode for mode in self.comparison_modes if mode not in SUPPORTED_COMPARISON_MODES
        ]
        if invalid_modes:
            msg = (
                "Unsupported comparison_modes: "
                + ", ".join(invalid_modes)
                + f". Expected subset of {sorted(SUPPORTED_COMPARISON_MODES)}."
            )
            raise ValueError(msg)
        self.matched_constraints_summary = {
            str(key): _scalar_value(value, name=f"matched_constraints_summary[{key!r}]")
            for key, value in self.matched_constraints_summary.items()
        }
        self.derived_ratios = {
            str(key): float(value) for key, value in self.derived_ratios.items()
        }
        self.report_metadata = {
            str(key): str(value) for key, value in self.report_metadata.items()
        }


@dataclass(slots=True)
class ExperimentConfig:
    """Top-level config for comparison-ready sequence experiments."""

    comparison_scope: str
    common_physics: CommonPhysicsConfig
    run_a: ExperimentRunConfig
    run_b: ExperimentRunConfig
    comparison_modes: tuple[str, ...]
    output: ExperimentOutputConfig = field(default_factory=ExperimentOutputConfig)

    def __post_init__(self) -> None:
        if self.comparison_scope not in SUPPORTED_COMPARISON_SCOPES:
            msg = (
                "comparison_scope must be one of "
                f"{sorted(SUPPORTED_COMPARISON_SCOPES)}."
            )
            raise ValueError(msg)
        if len(self.comparison_modes) == 0:
            msg = "comparison_modes must contain at least one entry."
            raise ValueError(msg)
        invalid_modes = [
            mode for mode in self.comparison_modes if mode not in SUPPORTED_COMPARISON_MODES
        ]
        if invalid_modes:
            msg = (
                "Unsupported comparison_modes: "
                + ", ".join(invalid_modes)
                + f". Expected subset of {sorted(SUPPORTED_COMPARISON_MODES)}."
            )
            raise ValueError(msg)
        self._validate_fastse_constraints()
        self._validate_vfa_fse_constraints()

    def _validate_fastse_constraints(self) -> None:
        runs = (self.run_a, self.run_b)
        if not any(run.sequence_family == SequenceFamily.FASTSE for run in runs):
            return
        if self.comparison_scope != "physics_only":
            msg = "FASTSE baseline currently supports comparison_scope='physics_only' only."
            raise ValueError(msg)
        invalid_modes = [
            mode for mode in self.comparison_modes if mode not in SUPPORTED_FASTSE_COMPARISON_MODES
        ]
        if invalid_modes:
            msg = (
                "FASTSE baseline does not support comparison_modes: "
                + ", ".join(invalid_modes)
                + f". Expected subset of {sorted(SUPPORTED_FASTSE_COMPARISON_MODES)}."
            )
            raise ValueError(msg)

    def _validate_vfa_fse_constraints(self) -> None:
        runs = (self.run_a, self.run_b)
        if not any(run.sequence_family == SequenceFamily.VFA_FSE for run in runs):
            return
        if self.comparison_scope != "physics_only":
            msg = "VFA_FSE_MANUAL currently supports comparison_scope='physics_only' only."
            raise ValueError(msg)
        invalid_modes = [
            mode for mode in self.comparison_modes if mode not in SUPPORTED_VFA_FSE_COMPARISON_MODES
        ]
        if invalid_modes:
            msg = (
                "VFA_FSE_MANUAL does not support comparison_modes: "
                + ", ".join(invalid_modes)
                + f". Expected subset of {sorted(SUPPORTED_VFA_FSE_COMPARISON_MODES)}."
            )
            raise ValueError(msg)

    @classmethod
    def from_yaml(cls, path: Path) -> ExperimentConfig:
        """Load an ExperimentConfig from YAML."""
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            msg = f"Expected mapping at YAML root in {path}."
            raise TypeError(msg)
        root = _mapping(raw)
        output_values = _optional_mapping(root.get("output"))
        raw_modes = root.get("comparison_modes", ["matched_resolution"])
        if not isinstance(raw_modes, list):
            msg = "comparison_modes must be a list."
            raise ValueError(msg)
        return cls(
            comparison_scope=str(root.get("comparison_scope", "physics_only")),
            common_physics=CommonPhysicsConfig.from_mapping(
                _mapping(_require_key(root, "common_physics"))
            ),
            run_a=ExperimentRunConfig.from_mapping(
                _mapping(_require_key(root, "run_a")),
                default_label="run_a",
            ),
            run_b=ExperimentRunConfig.from_mapping(
                _mapping(_require_key(root, "run_b")),
                default_label="run_b",
            ),
            comparison_modes=tuple(str(mode) for mode in raw_modes),
            output=ExperimentOutputConfig(summary_json=output_values.get("summary_json")),
        )

    def validate_supported_families(
        self,
        supported_families: set[SequenceFamily],
    ) -> None:
        """Raise a helpful error if a run uses an unsupported family."""
        unsupported = [
            run.sequence_family.value
            for run in (self.run_a, self.run_b)
            if run.sequence_family not in supported_families
        ]
        if unsupported:
            msg = (
                "Unsupported sequence families for this workflow: "
                + ", ".join(sorted(set(unsupported)))
            )
            raise ValueError(msg)

    def to_mapping(self) -> dict[str, Any]:
        """Return a YAML-compatible experiment mapping."""
        values: dict[str, Any] = {
            "comparison_scope": self.comparison_scope,
            "comparison_modes": list(self.comparison_modes),
            "common_physics": self.common_physics.to_mapping(),
            "run_a": self.run_a.to_mapping(),
            "run_b": self.run_b.to_mapping(),
        }
        output_values = self.output.to_mapping()
        if output_values:
            values["output"] = output_values
        return values

    def to_yaml(self, path: Path) -> None:
        """Write this experiment config as YAML."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(self.to_mapping(), sort_keys=False),
            encoding="utf-8",
        )

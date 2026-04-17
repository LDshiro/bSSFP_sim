"""Run-configuration models for the Chapter 4 compute CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import yaml

FloatArray = npt.NDArray[np.float64]
SUPPORTED_WAVEFORM_KINDS = frozenset({"hann", "rect"})


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    msg = "Expected a mapping-compatible value."
    raise TypeError(msg)


def _require_key(mapping: dict[str, Any], key: str) -> Any:
    value = mapping.get(key)
    if value is None:
        msg = f"Missing required key: {key}"
        raise ValueError(msg)
    return value


def _as_float_array(value: object, *, ndim: int, name: str) -> FloatArray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != ndim:
        msg = f"{name} must be a {ndim}D float array."
        raise ValueError(msg)
    return np.array(array, dtype=np.float64, copy=True)


@dataclass(slots=True)
class MetaConfig:
    """Metadata for one CLI compute run."""

    case_name: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.case_name:
            msg = "case_name must not be empty."
            raise ValueError(msg)


@dataclass(slots=True)
class PhysicsConfig:
    """Physical parameters for the compute CLI."""

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


@dataclass(slots=True)
class SequenceConfig:
    """Sequence controls for the Chapter 4 CLI."""

    tr_s: float
    rf_duration_s: float
    n_rf: int
    alpha_deg: float
    waveform_kind: str
    readout_fraction_of_free: float = 0.5

    def __post_init__(self) -> None:
        self.waveform_kind = self.waveform_kind.lower()
        if self.tr_s <= 0.0 or self.rf_duration_s <= 0.0:
            msg = "TR_s and rf_duration_s must be positive."
            raise ValueError(msg)
        if self.tr_s <= self.rf_duration_s:
            msg = "TR_s must be greater than rf_duration_s."
            raise ValueError(msg)
        if self.n_rf <= 0:
            msg = "n_rf must be positive."
            raise ValueError(msg)
        if self.alpha_deg <= 0.0:
            msg = "alpha_deg must be positive."
            raise ValueError(msg)
        if self.waveform_kind not in SUPPORTED_WAVEFORM_KINDS:
            msg = f"waveform_kind must be one of {sorted(SUPPORTED_WAVEFORM_KINDS)}."
            raise ValueError(msg)
        if not 0.0 <= self.readout_fraction_of_free <= 1.0:
            msg = "readout_fraction_of_free must be within [0, 1]."
            raise ValueError(msg)

    @property
    def alpha_rad(self) -> float:
        """Return the nominal flip angle in radians."""
        return float(np.deg2rad(self.alpha_deg))

    @property
    def free_duration_s(self) -> float:
        """Return the free-precession duration inside one TR."""
        return self.tr_s - self.rf_duration_s

    @property
    def readout_time_s(self) -> float:
        """Return the Chapter 4 readout time inside the 2TR superperiod."""
        return self.rf_duration_s + self.readout_fraction_of_free * self.free_duration_s


@dataclass(slots=True)
class PhaseCycleConfig:
    """Acquisition-wise phase cycles in degrees."""

    values_deg: FloatArray

    def __post_init__(self) -> None:
        self.values_deg = _as_float_array(self.values_deg, ndim=2, name="values_deg")
        if self.values_deg.shape[0] == 0:
            msg = "values_deg must contain at least one acquisition."
            raise ValueError(msg)
        if self.values_deg.shape[1] != 2:
            msg = "values_deg must have shape (n_acq, 2)."
            raise ValueError(msg)

    def build_values_rad(self) -> FloatArray:
        """Return the phase schedule in radians."""
        return np.asarray(np.deg2rad(self.values_deg), dtype=np.float64)

    @property
    def n_acquisitions(self) -> int:
        """Return the number of acquisitions."""
        return int(self.values_deg.shape[0])


@dataclass(slots=True)
class SweepConfig:
    """Off-resonance sweep definition."""

    start_hz: float
    stop_hz: float
    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            msg = "count must be positive."
            raise ValueError(msg)

    def build_delta_f_hz(self) -> FloatArray:
        """Build the sweep array from start/stop/count."""
        return np.linspace(self.start_hz, self.stop_hz, self.count, dtype=np.float64)


@dataclass(slots=True)
class IntegrationConfig:
    """RK integration settings for the compute CLI."""

    rk_method: str = "RK45"
    rk_rtol: float = 1.0e-7
    rk_atol: float = 1.0e-9
    rk_max_step_s: float = 5.0e-6
    rk_superperiods: int = 60
    save_every_time_step: bool = True

    def __post_init__(self) -> None:
        if not self.rk_method:
            msg = "rk_method must not be empty."
            raise ValueError(msg)
        if self.rk_rtol <= 0.0 or self.rk_atol <= 0.0:
            msg = "rk_rtol and rk_atol must be positive."
            raise ValueError(msg)
        if self.rk_max_step_s <= 0.0:
            msg = "rk_max_step_s must be positive."
            raise ValueError(msg)
        if self.rk_superperiods <= 0:
            msg = "rk_superperiods must be positive."
            raise ValueError(msg)


@dataclass(slots=True)
class OutputConfig:
    """Output-selection flags for Chapter 4 HDF5 files."""

    save_profiles: bool = True
    save_rk_trajectories: bool = True
    save_steady_state_orbit: bool = True
    save_fixed_points: bool = True


@dataclass(slots=True)
class RunConfig:
    """Full Chapter 4 compute configuration."""

    meta: MetaConfig
    physics: PhysicsConfig
    sequence: SequenceConfig
    phase_cycles: PhaseCycleConfig
    sweep: SweepConfig
    integration: IntegrationConfig = field(default_factory=IntegrationConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> RunConfig:
        """Load a RunConfig from a YAML file."""
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            msg = f"Expected mapping at YAML root in {path}."
            raise TypeError(msg)

        root = _mapping(raw)
        meta_values = _mapping(root.get("meta", {}))
        physics_values = _mapping(root.get("physics", {}))
        sequence_values = _mapping(root.get("sequence", {}))
        phase_values = _mapping(root.get("phase_cycles", {}))
        sweep_values = _mapping(root.get("sweep", {}))
        delta_f_values = _mapping(sweep_values.get("delta_f_hz", {}))
        integration_values = _mapping(root.get("integration", {}))
        output_values = _mapping(root.get("output", {}))

        return cls(
            meta=MetaConfig(
                case_name=str(meta_values.get("case_name", "")),
                description=str(meta_values.get("description", "")),
            ),
            physics=PhysicsConfig(
                t1_s=float(_require_key(physics_values, "T1_s")),
                t2_s=float(_require_key(physics_values, "T2_s")),
                m0=float(_require_key(physics_values, "M0")),
            ),
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
                rk_method=str(integration_values.get("rk_method", "RK45")),
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

    @property
    def n_acquisitions(self) -> int:
        """Return the number of acquisitions."""
        return self.phase_cycles.n_acquisitions

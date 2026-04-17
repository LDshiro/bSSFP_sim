"""Configuration models for the Chapter 3 solver and storage pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import yaml

from bssfpviz import __version__

FloatArray = npt.NDArray[np.float64]

DEFAULT_WINDOW_TITLE = "Bloch / bSSFP Visualizer - Chapter 3"
DEFAULT_PLACEHOLDER_TEXT = "Chapter 3 exact Bloch / steady-state pipeline"
DEFAULT_WINDOW_WIDTH = 960
DEFAULT_WINDOW_HEIGHT = 640

DEFAULT_T1_S = 0.040
DEFAULT_T2_S = 0.020
DEFAULT_M0 = 1.0
DEFAULT_GAMMA_RAD_PER_S_PER_T = 267_522_187.44

DEFAULT_RF_DURATION_S = 1.0e-3
DEFAULT_FREE_DURATION_S = 3.0e-3
DEFAULT_TR_S = DEFAULT_RF_DURATION_S + DEFAULT_FREE_DURATION_S
DEFAULT_TE_S = DEFAULT_RF_DURATION_S + 0.5 * DEFAULT_FREE_DURATION_S
DEFAULT_N_RF_SAMPLES = 100
DEFAULT_FLIP_ANGLE_RAD = float(np.pi / 3.0)
DEFAULT_N_CYCLES = 120

DEFAULT_PHASE_SCHEDULE_RAD = np.array([[0.0, 0.0], [0.0, np.pi]], dtype=np.float64)
DEFAULT_DELTA_F_HZ = np.array([-12.5, 0.0, 12.5], dtype=np.float64)

DEFAULT_RK_DT_S = 1.0e-5
DEFAULT_STEADY_STATE_DT_S = 1.0e-5
DEFAULT_N_STEADY_STATE_STEPS = 2 * DEFAULT_N_RF_SAMPLES + 3
DEFAULT_N_REFERENCE_STEPS = DEFAULT_N_CYCLES * (2 * DEFAULT_N_RF_SAMPLES + 2) + 1

SCHEMA_VERSION = "2.0"


def _utc_now_isoformat() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_float_array(value: object, *, ndim: int, name: str) -> FloatArray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != ndim:
        msg = f"{name} must be a {ndim}D float array."
        raise ValueError(msg)
    return np.array(array, dtype=np.float64, copy=True)


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    msg = "Expected a mapping-compatible value."
    raise TypeError(msg)


def _derived_time_step_counts(n_rf_samples: int, n_cycles: int) -> tuple[int, int]:
    n_steady_state_steps = 2 * n_rf_samples + 3
    n_reference_steps = n_cycles * (n_steady_state_steps - 1) + 1
    return n_reference_steps, n_steady_state_steps


@dataclass(slots=True)
class AppConfig:
    """Qt application window settings."""

    window_title: str = DEFAULT_WINDOW_TITLE
    placeholder_text: str = DEFAULT_PLACEHOLDER_TEXT
    window_width: int = DEFAULT_WINDOW_WIDTH
    window_height: int = DEFAULT_WINDOW_HEIGHT

    def __post_init__(self) -> None:
        if self.window_width <= 0 or self.window_height <= 0:
            msg = "Window size must be positive."
            raise ValueError(msg)


@dataclass(slots=True)
class PhysicsConfig:
    """Physical constants used by the Bloch model."""

    t1_s: float = DEFAULT_T1_S
    t2_s: float = DEFAULT_T2_S
    m0: float = DEFAULT_M0
    gamma_rad_per_s_per_t: float = DEFAULT_GAMMA_RAD_PER_S_PER_T

    def __post_init__(self) -> None:
        if self.t1_s <= 0.0 or self.t2_s <= 0.0:
            msg = "Relaxation times must be positive."
            raise ValueError(msg)
        if self.m0 <= 0.0:
            msg = "m0 must be positive."
            raise ValueError(msg)
        if self.gamma_rad_per_s_per_t <= 0.0:
            msg = "gamma_rad_per_s_per_t must be positive."
            raise ValueError(msg)

    @property
    def T1_s(self) -> float:
        """Return the Chapter 3 spec alias for `t1_s`."""
        return self.t1_s

    @property
    def T2_s(self) -> float:
        """Return the Chapter 3 spec alias for `t2_s`."""
        return self.t2_s

    @property
    def M0(self) -> float:
        """Return the Chapter 3 spec alias for `m0`."""
        return self.m0

    @property
    def gamma_rad_per_s_per_T(self) -> float:
        """Return the Chapter 3 spec alias for `gamma_rad_per_s_per_t`."""
        return self.gamma_rad_per_s_per_t


@dataclass(slots=True)
class SequenceConfig:
    """Sequence-level controls for the 2TR Chapter 3 model."""

    tr_s: float = DEFAULT_TR_S
    te_s: float = DEFAULT_TE_S
    rf_duration_s: float = DEFAULT_RF_DURATION_S
    free_duration_s: float = DEFAULT_FREE_DURATION_S
    n_rf_samples: int = DEFAULT_N_RF_SAMPLES
    flip_angle_rad: float = DEFAULT_FLIP_ANGLE_RAD
    phase_schedule_rad: FloatArray = field(
        default_factory=lambda: np.array(DEFAULT_PHASE_SCHEDULE_RAD, dtype=np.float64, copy=True)
    )
    n_cycles: int = DEFAULT_N_CYCLES

    def __post_init__(self) -> None:
        self.phase_schedule_rad = _as_float_array(
            self.phase_schedule_rad, ndim=2, name="phase_schedule_rad"
        )
        if self.phase_schedule_rad.shape[0] == 0:
            msg = "phase_schedule_rad must contain at least one acquisition."
            raise ValueError(msg)
        if self.phase_schedule_rad.shape[1] != 2:
            msg = "phase_schedule_rad must have shape (n_acq, 2) for the 2TR model."
            raise ValueError(msg)
        if self.tr_s <= 0.0 or self.te_s <= 0.0:
            msg = "TR and TE must be positive."
            raise ValueError(msg)
        if self.rf_duration_s <= 0.0 or self.free_duration_s < 0.0:
            msg = "RF and free durations must be non-negative."
            raise ValueError(msg)
        if self.n_rf_samples <= 0 or self.n_cycles <= 0:
            msg = "n_rf_samples and n_cycles must be positive."
            raise ValueError(msg)
        if self.flip_angle_rad <= 0.0:
            msg = "flip_angle_rad must be positive."
            raise ValueError(msg)
        expected_tr_s = self.rf_duration_s + self.free_duration_s
        if not np.isclose(self.tr_s, expected_tr_s, atol=1e-15, rtol=0.0):
            msg = "tr_s must equal rf_duration_s + free_duration_s in Chapter 3."
            raise ValueError(msg)
        expected_te_s = self.rf_duration_s + 0.5 * self.free_duration_s
        if not np.isclose(self.te_s, expected_te_s, atol=1e-15, rtol=0.0):
            msg = "te_s must equal rf_duration_s + free_duration_s / 2 in Chapter 3."
            raise ValueError(msg)

    @property
    def TR_s(self) -> float:
        """Return the Chapter 3 spec alias for `tr_s`."""
        return self.tr_s

    @property
    def TE_s(self) -> float:
        """Return the Chapter 3 spec alias for `te_s`."""
        return self.te_s

    @property
    def n_acquisitions(self) -> int:
        """Return the number of phase-cycled acquisitions."""
        return int(self.phase_schedule_rad.shape[0])

    @property
    def n_pulses_per_superperiod(self) -> int:
        """Return the number of pulses in one 2TR superperiod."""
        return int(self.phase_schedule_rad.shape[1])


@dataclass(slots=True)
class SamplingConfig:
    """Frequency sweep and RK sampling controls."""

    delta_f_hz: FloatArray = field(
        default_factory=lambda: np.array(DEFAULT_DELTA_F_HZ, dtype=np.float64, copy=True)
    )
    rk_dt_s: float = DEFAULT_RK_DT_S
    steady_state_dt_s: float = DEFAULT_STEADY_STATE_DT_S
    n_reference_steps: int = DEFAULT_N_REFERENCE_STEPS
    n_steady_state_steps: int = DEFAULT_N_STEADY_STATE_STEPS

    def __post_init__(self) -> None:
        self.delta_f_hz = _as_float_array(self.delta_f_hz, ndim=1, name="delta_f_hz")
        if self.delta_f_hz.size == 0:
            msg = "delta_f_hz must not be empty."
            raise ValueError(msg)
        if self.rk_dt_s <= 0.0 or self.steady_state_dt_s <= 0.0:
            msg = "rk_dt_s and steady_state_dt_s must be positive."
            raise ValueError(msg)
        if self.n_reference_steps <= 0 or self.n_steady_state_steps <= 0:
            msg = "n_reference_steps and n_steady_state_steps must be positive."
            raise ValueError(msg)

    @property
    def n_spins(self) -> int:
        """Return the number of frequency samples."""
        return int(self.delta_f_hz.shape[0])

    @property
    def delta_omega_rad_s(self) -> FloatArray:
        """Return the off-resonance sweep in rad/s."""
        return np.asarray(2.0 * np.pi * self.delta_f_hz, dtype=np.float64)


@dataclass(slots=True)
class SimulationConfig:
    """Simulation settings used by the Chapter 3 compute pipeline."""

    physics: PhysicsConfig = field(default_factory=PhysicsConfig)
    sequence: SequenceConfig = field(default_factory=SequenceConfig)
    sampling: SamplingConfig = field(default_factory=SamplingConfig)

    def __post_init__(self) -> None:
        expected_reference_steps, expected_steady_state_steps = _derived_time_step_counts(
            self.sequence.n_rf_samples, self.sequence.n_cycles
        )
        if self.sampling.n_reference_steps != expected_reference_steps:
            msg = (
                "n_reference_steps must equal "
                f"{expected_reference_steps} for n_rf_samples={self.sequence.n_rf_samples} "
                f"and n_cycles={self.sequence.n_cycles}."
            )
            raise ValueError(msg)
        if self.sampling.n_steady_state_steps != expected_steady_state_steps:
            msg = (
                "n_steady_state_steps must equal "
                f"{expected_steady_state_steps} for n_rf_samples={self.sequence.n_rf_samples}."
            )
            raise ValueError(msg)

    @property
    def n_acquisitions(self) -> int:
        """Return the number of phase-cycled acquisitions."""
        return self.sequence.n_acquisitions

    @property
    def n_pulses_per_superperiod(self) -> int:
        """Return the number of pulses in the 2TR superperiod."""
        return self.sequence.n_pulses_per_superperiod

    @property
    def n_spins(self) -> int:
        """Return the number of off-resonance samples."""
        return self.sampling.n_spins

    @property
    def phase_schedule_rad(self) -> FloatArray:
        """Return the phase schedule for compatibility with Chapter 2 callers."""
        return self.sequence.phase_schedule_rad

    @property
    def superperiod_duration_s(self) -> float:
        """Return the 2TR superperiod duration."""
        return 2.0 * self.sequence.tr_s


@dataclass(slots=True)
class ProjectConfig:
    """Root configuration model for GUI and simulation settings."""

    app: AppConfig = field(default_factory=AppConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)


def load_project_config(path: str | Path) -> ProjectConfig:
    """Load a ProjectConfig instance from a YAML file."""
    config_path = Path(path)
    raw_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw_data, dict):
        msg = f"Expected mapping at YAML root in {config_path}"
        raise TypeError(msg)

    root_values = _mapping(raw_data)
    app_values = _mapping(root_values.get("app"))
    simulation_values = _mapping(root_values.get("simulation", root_values))
    physics_values = _mapping(simulation_values.get("physics"))
    sequence_values = _mapping(simulation_values.get("sequence"))
    sampling_values = _mapping(simulation_values.get("sampling"))

    tr_s = float(sequence_values.get("tr_s", DEFAULT_TR_S))
    rf_duration_s = float(sequence_values.get("rf_duration_s", DEFAULT_RF_DURATION_S))
    free_duration_s = float(sequence_values.get("free_duration_s", DEFAULT_FREE_DURATION_S))
    n_rf_samples = int(sequence_values.get("n_rf_samples", DEFAULT_N_RF_SAMPLES))
    n_cycles = int(sequence_values.get("n_cycles", DEFAULT_N_CYCLES))
    default_reference_steps, default_steady_state_steps = _derived_time_step_counts(
        n_rf_samples, n_cycles
    )

    sequence = SequenceConfig(
        tr_s=tr_s,
        te_s=float(sequence_values.get("te_s", rf_duration_s + 0.5 * free_duration_s)),
        rf_duration_s=rf_duration_s,
        free_duration_s=free_duration_s,
        n_rf_samples=n_rf_samples,
        flip_angle_rad=float(sequence_values.get("flip_angle_rad", DEFAULT_FLIP_ANGLE_RAD)),
        phase_schedule_rad=sequence_values.get(
            "phase_schedule_rad",
            simulation_values.get("phase_schedule_rad", DEFAULT_PHASE_SCHEDULE_RAD.tolist()),
        ),
        n_cycles=n_cycles,
    )
    sampling = SamplingConfig(
        delta_f_hz=sampling_values.get("delta_f_hz", DEFAULT_DELTA_F_HZ.tolist()),
        rk_dt_s=float(sampling_values.get("rk_dt_s", DEFAULT_RK_DT_S)),
        steady_state_dt_s=float(
            sampling_values.get("steady_state_dt_s", DEFAULT_STEADY_STATE_DT_S)
        ),
        n_reference_steps=int(sampling_values.get("n_reference_steps", default_reference_steps)),
        n_steady_state_steps=int(
            sampling_values.get("n_steady_state_steps", default_steady_state_steps)
        ),
    )

    return ProjectConfig(
        app=AppConfig(
            window_title=str(app_values.get("window_title", DEFAULT_WINDOW_TITLE)),
            placeholder_text=str(app_values.get("placeholder_text", DEFAULT_PLACEHOLDER_TEXT)),
            window_width=int(app_values.get("window_width", DEFAULT_WINDOW_WIDTH)),
            window_height=int(app_values.get("window_height", DEFAULT_WINDOW_HEIGHT)),
        ),
        simulation=SimulationConfig(
            physics=PhysicsConfig(
                t1_s=float(physics_values.get("t1_s", DEFAULT_T1_S)),
                t2_s=float(physics_values.get("t2_s", DEFAULT_T2_S)),
                m0=float(physics_values.get("m0", DEFAULT_M0)),
                gamma_rad_per_s_per_t=float(
                    physics_values.get("gamma_rad_per_s_per_t", DEFAULT_GAMMA_RAD_PER_S_PER_T)
                ),
            ),
            sequence=sequence,
            sampling=sampling,
        ),
    )


def load_app_config(path: str | Path) -> AppConfig:
    """Load only the GUI portion of the project configuration."""
    return load_project_config(path).app


def load_simulation_config(path: str | Path) -> SimulationConfig:
    """Load only the simulation portion of the project configuration."""
    return load_project_config(path).simulation


@dataclass(slots=True)
class SimulationMetadata:
    """Metadata stored alongside a SimulationDataset."""

    schema_version: str = SCHEMA_VERSION
    created_at_utc: str = field(default_factory=_utc_now_isoformat)
    app_name: str = "bloch-ssfp-visualizer"
    app_version: str = __version__
    git_commit: str = "unknown"
    run_name: str = "chapter3_demo"
    user_notes: str = ""

    def __post_init__(self) -> None:
        if not self.schema_version:
            msg = "schema_version must not be empty."
            raise ValueError(msg)
        if not self.created_at_utc:
            msg = "created_at_utc must not be empty."
            raise ValueError(msg)
        if not self.app_name or not self.app_version:
            msg = "app_name and app_version must not be empty."
            raise ValueError(msg)

"""Legacy bSSFP compute runner built on the family-specific backend."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

from bssfpviz.models.run_config import RunConfig
from bssfpviz.sequences.bssfp.legacy_io import save_legacy_bssfp_result
from bssfpviz.sequences.bssfp.runner import run_bssfp_simulation


@dataclass(slots=True)
class ComputeSummary:
    """High-level summary of one legacy bSSFP compute run."""

    case_name: str
    n_acquisitions: int
    n_delta_f: int
    n_time_samples: int
    output_path: Path
    elapsed_seconds: float
    min_profile_individual: float
    max_profile_individual: float
    min_profile_sos: float
    max_profile_sos: float

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        data = asdict(self)
        data["output_path"] = str(self.output_path)
        return data


def run_compute(config: RunConfig, output_path: Path) -> ComputeSummary:
    """Run the legacy bSSFP compute workflow and save its HDF5 output."""
    start_time = perf_counter()
    result = run_bssfp_simulation(config, run_label="legacy_compute")
    save_legacy_bssfp_result(output_path, config, result)

    elapsed_seconds = perf_counter() - start_time
    return ComputeSummary(
        case_name=config.meta.case_name,
        n_acquisitions=int(result.scalars["n_acquisitions"]),
        n_delta_f=int(result.scalars["n_delta_f"]),
        n_time_samples=int(result.scalars["n_rk_time_samples"]),
        output_path=output_path,
        elapsed_seconds=elapsed_seconds,
        min_profile_individual=float(result.scalars["individual_profile_abs_min"]),
        max_profile_individual=float(result.scalars["individual_profile_abs_max"]),
        min_profile_sos=float(result.scalars["sos_profile_abs_min"]),
        max_profile_sos=float(result.scalars["sos_profile_abs_max"]),
    )

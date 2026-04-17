"""Session state for the Chapter 7 comparison GUI."""

from __future__ import annotations

from dataclasses import dataclass, field

VALID_ACTIVE_SLOTS = {"primary", "compare"}
VALID_MODES = {"reference", "steady"}


@dataclass(slots=True)
class SessionState:
    """Serializable GUI/session state for comparison playback."""

    primary_path: str | None = None
    compare_path: str | None = None
    active_slot: str = "primary"
    compare_enabled: bool = False
    compare_visible_in_scene: bool = True
    thick_all_spins_in_scene: bool = False
    mode: str = "reference"
    acquisition_index: int = 0
    frame_index: int = 0
    fps: float = 30.0
    loop: bool = True
    selected_delta_f_hz: float | None = None
    bookmarks_hz: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.active_slot not in VALID_ACTIVE_SLOTS:
            msg = f"active_slot must be one of {sorted(VALID_ACTIVE_SLOTS)}."
            raise ValueError(msg)
        if self.mode not in VALID_MODES:
            msg = f"mode must be one of {sorted(VALID_MODES)}."
            raise ValueError(msg)
        if self.fps <= 0.0:
            msg = "fps must be positive."
            raise ValueError(msg)
        if self.acquisition_index < 0 or self.frame_index < 0:
            msg = "acquisition_index and frame_index must be non-negative."
            raise ValueError(msg)
        if self.selected_delta_f_hz is not None:
            self.selected_delta_f_hz = float(self.selected_delta_f_hz)
        self.bookmarks_hz = [float(value) for value in self.bookmarks_hz]

    def normalized_bookmarks(self) -> list[float]:
        """Return sorted bookmarks with duplicates merged at 1e-9 tolerance."""
        if not self.bookmarks_hz:
            return []
        ordered = sorted(float(value) for value in self.bookmarks_hz)
        normalized: list[float] = [ordered[0]]
        for value in ordered[1:]:
            if abs(value - normalized[-1]) <= 1.0e-9:
                continue
            normalized.append(value)
        return normalized

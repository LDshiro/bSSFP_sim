"""Unit tests for Chapter 7 session state and JSON persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from bssfpviz.gui.session_state import SessionState
from bssfpviz.io.session_json import load_session_json, save_session_json


def test_session_state_json_round_trip(tmp_path: Path) -> None:
    session = SessionState(
        primary_path="primary.h5",
        compare_path="compare.h5",
        active_slot="compare",
        compare_enabled=True,
        compare_visible_in_scene=False,
        mode="steady",
        acquisition_index=1,
        frame_index=3,
        fps=20.0,
        loop=False,
        selected_delta_f_hz=12.5,
        bookmarks_hz=[125.0, 0.0, 125.0 + 1.0e-10],
    )
    path = tmp_path / "session.json"

    save_session_json(path, session)
    loaded = load_session_json(path)

    assert loaded.primary_path == "primary.h5"
    assert loaded.compare_path == "compare.h5"
    assert loaded.active_slot == "compare"
    assert loaded.mode == "steady"
    assert loaded.fps == 20.0
    assert loaded.bookmarks_hz == [0.0, 125.0]


@pytest.mark.parametrize(
    ("kwargs", "expected_message"),
    [
        ({"active_slot": "invalid"}, "active_slot"),
        ({"mode": "invalid"}, "mode"),
        ({"fps": 0.0}, "fps"),
    ],
)
def test_session_state_validation_errors(kwargs: dict[str, object], expected_message: str) -> None:
    with pytest.raises(ValueError, match=expected_message):
        SessionState(**kwargs)

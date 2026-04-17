"""Integration tests for booting the Chapter 7 Qt application window."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from bssfpviz.gui.main_window import MainWindow


def test_main_window_boots_headless(monkeypatch: pytest.MonkeyPatch, qapp: object) -> None:
    _ = qapp
    monkeypatch.setenv("BSSFPVIZ_DISABLE_3D", "1")
    window = MainWindow()
    window.show()

    assert window.windowTitle() == "Bloch / bSSFP Visualizer - Chapter 7"
    assert window.config_editor is not None
    assert window.profile_panel is not None

    window.close()

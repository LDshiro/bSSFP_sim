"""Application launcher for the Chapter 7 GUI."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from bssfpviz.gui.main_window import MainWindow
from bssfpviz.models.config import AppConfig


def create_application() -> QApplication:
    """Return a QApplication instance, creating one when needed."""
    existing_app = QApplication.instance()
    if isinstance(existing_app, QApplication):
        return existing_app
    if existing_app is not None:
        msg = "A non-GUI Qt application instance already exists."
        raise RuntimeError(msg)
    return QApplication(sys.argv)


def main() -> int:
    """Launch the Chapter 7 GUI application."""
    app = create_application()
    window = MainWindow(
        config=AppConfig(
            window_title="Bloch / bSSFP Visualizer - Chapter 7",
            placeholder_text="Chapter 7 comparison, session, and export GUI",
            window_width=1520,
            window_height=980,
        )
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

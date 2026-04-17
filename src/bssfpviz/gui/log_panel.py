"""Log output panel for the Chapter 5 GUI."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class LogPanel(QWidget):
    """Read-only log sink used by the main window and worker."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setObjectName("log-text")
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

    def append_log(self, message: str) -> None:
        """Append one timestamped log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.text_edit.appendPlainText(f"[{timestamp}] {message}")

    def clear_log(self) -> None:
        """Clear the log output."""
        self.text_edit.clear()

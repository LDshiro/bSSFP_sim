"""Background compute worker used by the Chapter 5 GUI."""

from __future__ import annotations

from pathlib import Path
from traceback import format_exc
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from bssfpviz.gui.adapters import run_compute_adapter


class ComputeWorker(QObject):
    """Run the Chapter 4 compute workflow outside the GUI thread."""

    finished = Signal(object, object)
    failed = Signal(str, str)
    log = Signal(str)

    def __init__(self, config: Any, output_path: Path) -> None:
        super().__init__()
        self._config = config
        self._output_path = output_path

    @Slot()
    def run(self) -> None:
        """Execute the compute adapter and emit success or failure signals."""
        self.log.emit(f"compute started: {self._output_path}")
        try:
            summary = run_compute_adapter(self._config, self._output_path)
        except Exception as exc:  # noqa: BLE001
            tb = format_exc()
            self.log.emit(f"compute failed: {exc}")
            self.failed.emit(str(exc), tb)
            return

        self.log.emit(f"compute finished: {self._output_path}")
        self.finished.emit(summary, self._output_path)

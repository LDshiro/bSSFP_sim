"""Background worker for generic comparison runs."""

from __future__ import annotations

from pathlib import Path
from traceback import format_exc

from PySide6.QtCore import QObject, Signal, Slot

from bssfpviz.models.comparison import ExperimentConfig
from bssfpviz.workflows.compare import run_comparison


class CompareWorker(QObject):
    """Run the generic comparison workflow outside the GUI thread."""

    finished = Signal(object, object)
    failed = Signal(str, str)
    log = Signal(str)

    def __init__(self, config: ExperimentConfig, output_path: Path) -> None:
        super().__init__()
        self._config = config
        self._output_path = output_path

    @Slot()
    def run(self) -> None:
        """Execute the comparison workflow and emit success/failure signals."""
        self.log.emit(f"comparison started: {self._output_path}")
        try:
            summary = run_comparison(self._config, self._output_path)
        except Exception as exc:  # noqa: BLE001
            tb = format_exc()
            self.log.emit(f"comparison failed: {exc}")
            self.failed.emit(str(exc), tb)
            return

        self.log.emit(f"comparison finished: {self._output_path}")
        self.finished.emit(summary, self._output_path)

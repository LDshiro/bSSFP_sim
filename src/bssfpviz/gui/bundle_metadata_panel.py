"""Bundle metadata panel for the generic comparison inspector shell."""

from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from bssfpviz.gui.bundle_view_models import BundleMetadataViewModel


class BundleMetadataPanel(QWidget):
    """Read-only text view for loaded comparison bundle metadata."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setObjectName("bundle-metadata-text")
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)
        self.clear()

    def clear(self) -> None:
        """Reset the panel to its empty state."""
        self.text_edit.setPlainText("Load a comparison bundle to inspect metadata.")

    def set_view_model(self, model: BundleMetadataViewModel) -> None:
        """Render one bundle metadata view-model."""
        self.text_edit.setPlainText(model.text)

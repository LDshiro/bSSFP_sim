"""Bookmark management widget for Chapter 7."""

from __future__ import annotations

from contextlib import suppress

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bssfpviz.gui.comparison_controller import ComparisonController


class BookmarkPanel(QWidget):
    """Show, add, remove, and jump to delta-f bookmarks."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller: ComparisonController | None = None
        self._build_ui()

    def set_controller(self, controller: ComparisonController | None) -> None:
        """Attach one comparison controller."""
        if self._controller is controller:
            self.refresh()
            return

        if self._controller is not None:
            with suppress(TypeError):
                self._controller.bookmarks_changed.disconnect(self.refresh)

        self._controller = controller
        if controller is not None:
            controller.bookmarks_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        """Refresh the bookmark list from the controller."""
        self.list_widget.clear()
        if self._controller is None:
            return
        for value in self._controller.session_state().normalized_bookmarks():
            item = QListWidgetItem(_format_hz(value), self.list_widget)
            item.setData(Qt.ItemDataRole.UserRole, value)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add current", self)
        self.add_button.setObjectName("bookmark-add-button")
        self.remove_button = QPushButton("Remove selected", self)
        self.remove_button.setObjectName("bookmark-remove-button")
        self.jump_button = QPushButton("Jump", self)
        self.jump_button.setObjectName("bookmark-jump-button")

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.jump_button)

        self.list_widget = QListWidget(self)
        self.list_widget.setObjectName("bookmark-list")

        layout.addLayout(button_layout)
        layout.addWidget(self.list_widget, 1)

        self.add_button.clicked.connect(self._on_add_clicked)
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.jump_button.clicked.connect(self._on_jump_clicked)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

    def _selected_value(self) -> float | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return None if data is None else float(data)

    def _on_add_clicked(self) -> None:
        if self._controller is not None:
            self._controller.add_bookmark()

    def _on_remove_clicked(self) -> None:
        value = self._selected_value()
        if self._controller is not None and value is not None:
            self._controller.remove_bookmark(value)

    def _on_jump_clicked(self) -> None:
        value = self._selected_value()
        if self._controller is not None and value is not None:
            self._controller.jump_to_bookmark(value)

    def _on_item_double_clicked(self, _item: QListWidgetItem) -> None:
        self._on_jump_clicked()


def _format_hz(value: float) -> str:
    return f"{value:+.3f} Hz"

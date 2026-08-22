"""EmptyState: icon + helper text + optional call-to-action, shown by DataTable in place of a
table that has zero rows instead of a blank white void."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ui.theme import Colors, icon


class EmptyState(QWidget):
    def __init__(
        self,
        icon_name: str,
        text: str,
        action_label: str | None = None,
        on_action=None,
        parent=None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setProperty("role", "emptyIcon")
        icon_label.setPixmap(icon(icon_name, Colors.BORDER_STRONG).pixmap(QSize(48, 48)))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        text_label = QLabel(text)
        text_label.setProperty("role", "emptyText")
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)

        if action_label:
            btn = QPushButton(action_label)
            btn.setProperty("secondary", True)
            btn.setCursor(Qt.PointingHandCursor)
            if on_action:
                btn.clicked.connect(on_action)
            layout.addWidget(btn, alignment=Qt.AlignCenter)

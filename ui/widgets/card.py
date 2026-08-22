"""Card: a generic 'section container' — replaces raw QGroupBox usage across the app so every
screen gets the same padding, border, radius, and shadow (see ui/theme.py Radius.CARD)."""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.theme import apply_card_shadow


class Card(QFrame):
    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        apply_card_shadow(self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        self._header_actions = QHBoxLayout()
        self._header_actions.setSpacing(8)

        if title:
            header = QHBoxLayout()
            title_label = QLabel(title)
            title_label.setProperty("role", "cardTitle")
            header.addWidget(title_label)
            header.addStretch()
            header.addLayout(self._header_actions)
            outer.addLayout(header)

            divider = QFrame()
            divider.setObjectName("cardDivider")
            divider.setFixedHeight(1)
            outer.addWidget(divider)

        self.body = QVBoxLayout()
        self.body.setSpacing(14)
        outer.addLayout(self.body)

    def add_header_action(self, widget: QWidget):
        self._header_actions.addWidget(widget)

"""StatCard: a KPI tile — a bold gradient top bar, a solid gradient icon circle, big bold
number, muted label, optional delta.

Used by the Reports screen; `accent` should always be one of ui.theme.Colors so every hardcoded
color still traces back to the token file (the gradient itself is derived here from that single
accent color, so callers never need to hand in a matching light/dark pair).
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.theme import Radius, apply_card_shadow, icon


def _gradient_css(hex_color: str) -> str:
    base = QColor(hex_color)
    light = base.lighter(140)
    return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {light.name()}, stop:1 {base.name()})"


class StatCard(QFrame):
    def __init__(self, icon_name: str, label: str, accent: str, delta: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        apply_card_shadow(self)

        gradient = _gradient_css(accent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        accent_bar = QFrame()
        accent_bar.setFixedHeight(4)
        accent_bar.setStyleSheet(
            f"background: {gradient}; "
            f"border-top-left-radius: {Radius.CARD}px; border-top-right-radius: {Radius.CARD}px;"
        )
        outer.addWidget(accent_bar)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        circle = QFrame()
        circle.setObjectName("statIconCircle")
        circle.setFixedSize(44, 44)
        circle.setStyleSheet(f"QFrame#statIconCircle {{ background: {gradient}; }}")
        circle_layout = QVBoxLayout(circle)
        circle_layout.setContentsMargins(0, 0, 0, 0)
        circle_layout.setAlignment(Qt.AlignCenter)
        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name, "white").pixmap(QSize(20, 20)))
        circle_layout.addWidget(icon_label)
        layout.addWidget(circle, alignment=Qt.AlignLeft)

        self.value_label = QLabel("0")
        self.value_label.setProperty("role", "statValue")
        layout.addWidget(self.value_label)

        label_row = QHBoxLayout()
        caption = QLabel(label)
        caption.setProperty("role", "statLabel")
        label_row.addWidget(caption)
        label_row.addStretch()
        self.delta_label = None
        if delta:
            self.delta_label = QLabel(delta)
            self.delta_label.setProperty("role", "statDelta")
            label_row.addWidget(self.delta_label)
        layout.addLayout(label_row)

        outer.addWidget(content)

    def set_value(self, text: str):
        self.value_label.setText(text)

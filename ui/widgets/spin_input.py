"""SpinInput: a QSpinBox with its native (RTL-broken) up/down arrows hidden — see
`QSpinBox::up-button/down-button { width: 0px; }` in ui/style.qss — replaced with explicit
`-`/`+` QPushButtons. Behaves like a normal QSpinBox: `.value()`, `.setValue()`,
`.valueChanged` all work since the QSpinBox itself is exposed as `.spinbox`.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSpinBox, QWidget

from ui.theme import Colors, icon


class SpinInput(QWidget):
    def __init__(
        self,
        minimum: int = 0,
        maximum: int = 999_999_999,
        value: int = 0,
        suffix: str = "",
        parent=None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.minus_btn = QPushButton()
        self.minus_btn.setIcon(icon("fa5s.minus", Colors.TEXT_SECONDARY))
        self.minus_btn.setFixedSize(32, 32)
        self.minus_btn.setProperty("secondary", True)
        self.minus_btn.setCursor(Qt.PointingHandCursor)

        self.spinbox = QSpinBox()
        self.spinbox.setRange(minimum, maximum)
        self.spinbox.setValue(value)
        if suffix:
            self.spinbox.setSuffix(suffix)
        self.spinbox.setAlignment(Qt.AlignCenter)
        self.spinbox.setMinimumHeight(36)

        self.plus_btn = QPushButton()
        self.plus_btn.setIcon(icon("fa5s.plus", Colors.PRIMARY))
        self.plus_btn.setFixedSize(32, 32)
        self.plus_btn.setProperty("secondary", True)
        self.plus_btn.setCursor(Qt.PointingHandCursor)

        self.minus_btn.clicked.connect(self.spinbox.stepDown)
        self.plus_btn.clicked.connect(self.spinbox.stepUp)

        layout.addWidget(self.minus_btn)
        layout.addWidget(self.spinbox, 1)
        layout.addWidget(self.plus_btn)

        self.valueChanged = self.spinbox.valueChanged

    def value(self) -> int:
        return self.spinbox.value()

    def setValue(self, value: int):
        self.spinbox.setValue(value)

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        self.spinbox.setEnabled(enabled)
        self.minus_btn.setEnabled(enabled)
        self.plus_btn.setEnabled(enabled)

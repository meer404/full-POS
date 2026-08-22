"""TopBar: page title (right, RTL-leading edge) + a live date/clock (left) via QTimer.

Pure UI chrome, no DB access. `MainWindow` calls `set_title()` when the sidebar selection
changes.
"""
from __future__ import annotations

from PySide6.QtCore import QDateTime, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class TopBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(64)

        row = QHBoxLayout(self)
        row.setContentsMargins(24, 0, 24, 0)
        row.setSpacing(12)

        self.title_label = QLabel("")
        self.title_label.setProperty("role", "title")
        row.addWidget(self.title_label)
        row.addStretch()

        self.clock_label = QLabel("")
        self.clock_label.setProperty("role", "caption")
        row.addWidget(self.clock_label)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    def set_title(self, title: str):
        self.title_label.setText(title)

    def _tick(self):
        now = QDateTime.currentDateTime()
        self.clock_label.setText(now.toString("yyyy/MM/dd — HH:mm:ss"))

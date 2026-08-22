"""Badge: small status pill (Expired/Expiring/Low stock/OK, admin/cashier role tags, ...).

`kind` must match one of the `QLabel[badge="..."]` selectors in ui/style.qss:
success, warning, danger, info, admin, cashier.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class Badge(QLabel):
    def __init__(self, text: str, kind: str = "info", parent=None):
        super().__init__(text, parent)
        self.setProperty("badge", kind)
        self.setAlignment(Qt.AlignCenter)

    def set_kind(self, kind: str):
        self.setProperty("badge", kind)
        self.style().unpolish(self)
        self.style().polish(self)

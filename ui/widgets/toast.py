"""Toast (non-blocking success/error notification) + confirm() (blocking confirmation dialog
for destructive actions). Both replace bare QMessageBox usage.

Toast is only ever triggered from UI-facing on_X_clicked slots, never from the headless
save()/complete_sale()-style core logic methods, so it never runs under
QT_QPA_PLATFORM=offscreen tests. Same for confirm().
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.theme import apply_card_shadow, icon


class Toast(QFrame):
    def __init__(self, parent: QWidget, message: str, kind: str = "success"):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setProperty("kind", kind)
        self.setAttribute(Qt.WA_StyledBackground, True)
        apply_card_shadow(self, blur=20, y_offset=4, alpha=60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        icon_name = "fa5s.check-circle" if kind == "success" else "fa5s.exclamation-circle"
        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name, "white").pixmap(QSize(16, 16)))
        layout.addWidget(icon_label)

        text_label = QLabel(message)
        layout.addWidget(text_label)

        self.style().unpolish(self)
        self.style().polish(self)
        self.adjustSize()

    def show_at_top_left(self, margin: int = 24, duration_ms: int = 3000):
        end_pos = QPoint(margin, margin)
        start_pos = QPoint(margin, -self.height() - 10)
        self.move(start_pos)
        self.show()
        self.raise_()

        self._slide_in = QPropertyAnimation(self, b"pos", self)
        self._slide_in.setDuration(220)
        self._slide_in.setStartValue(start_pos)
        self._slide_in.setEndValue(end_pos)
        self._slide_in.setEasingCurve(QEasingCurve.OutCubic)
        self._slide_in.start()

        QTimer.singleShot(duration_ms, self._start_dismiss)

    def _start_dismiss(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        self._fade_out = QPropertyAnimation(effect, b"opacity", self)
        self._fade_out.setDuration(220)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self._dismiss)
        self._fade_out.start()

    def _dismiss(self):
        self.close()
        self.deleteLater()


def show_toast(window: QWidget, message: str, kind: str = "success") -> Toast:
    toast = Toast(window, message, kind)
    toast.show_at_top_left()
    return toast


def confirm(parent: QWidget, message: str, title: str = "دڵنیابوونەوە") -> bool:
    """Blocking Yes/No confirmation for a destructive action. Returns True only if the user
    confirms."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLayoutDirection(Qt.RightToLeft)
    dialog.setMinimumWidth(340)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(20)

    label = QLabel(message)
    label.setWordWrap(True)
    layout.addWidget(label)

    btn_row = QHBoxLayout()
    btn_row.setSpacing(10)
    confirm_btn = QPushButton("دڵنیام، بیسڕەوە")
    confirm_btn.setProperty("danger", True)
    cancel_btn = QPushButton("پاشگەزبوونەوە")
    cancel_btn.setProperty("secondary", True)
    for btn in (confirm_btn, cancel_btn):
        btn.setCursor(Qt.PointingHandCursor)
    btn_row.addWidget(confirm_btn)
    btn_row.addWidget(cancel_btn)
    layout.addLayout(btn_row)

    cancel_btn.clicked.connect(dialog.reject)
    confirm_btn.clicked.connect(dialog.accept)
    confirm_btn.setDefault(True)

    return dialog.exec() == QDialog.Accepted

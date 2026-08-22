"""Small, centralized motion helpers — the "bold & vivid + micro-interactions" pass.

Qt stylesheets have no `transition` support, so any animation has to be hand-driven with
QPropertyAnimation. Keeping it centralized here (one app-wide event filter for button press
feedback, one helper each for the sidebar indicator and the toast slide) means individual
screens don't need to know animation exists — they just use a normal QPushButton/Sidebar/Toast.
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, QRect
from PySide6.QtWidgets import QGraphicsOpacityEffect, QPushButton, QWidget


class ButtonPressFeedback(QObject):
    """App-wide event filter: every enabled QPushButton gets a quick opacity dip on press,
    so clicking anything in the app feels tactile without touching each button individually."""

    def eventFilter(self, watched, event):
        if isinstance(watched, QPushButton) and watched.isEnabled():
            if event.type() == QEvent.MouseButtonPress:
                self._pulse(watched)
        return False

    @staticmethod
    def _pulse(button: QPushButton):
        effect = button.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(button)
            button.setGraphicsEffect(effect)
        effect.setOpacity(1.0)
        anim = QPropertyAnimation(effect, b"opacity", button)
        anim.setDuration(140)
        anim.setStartValue(0.65)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        button._press_anim = anim  # keep a live reference so it isn't GC'd mid-flight


def install_button_feedback(app) -> ButtonPressFeedback:
    feedback = ButtonPressFeedback(app)
    app.installEventFilter(feedback)
    return feedback


def animate_slide(widget: QWidget, start: QRect, end: QRect, duration: int = 220, on_finished=None):
    """Animate `widget.geometry()` from `start` to `end`. Returns the animation (caller should
    keep a reference, e.g. store it on the widget, so it isn't garbage-collected mid-flight)."""
    anim = QPropertyAnimation(widget, b"geometry", widget)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    if on_finished:
        anim.finished.connect(on_finished)
    anim.start()
    return anim

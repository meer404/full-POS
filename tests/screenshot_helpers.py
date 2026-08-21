"""Helper for saving offscreen PNG screenshots of a widget/dialog during the UI redesign pass.

Not a test itself — imported by ad-hoc screenshot scripts. Requires QT_QPA_PLATFORM=offscreen.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget


def save_screenshot(widget: QWidget, path: str | Path, size: tuple[int, int] | None = None) -> Path:
    """Show `widget` off-screen, let layout settle, grab it, and save as a PNG at `path`."""
    if size is not None:
        widget.resize(*size)
    widget.show()

    app = QApplication.instance()
    for _ in range(5):
        app.processEvents()

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pixmap = widget.grab()
    pixmap.save(str(path), "PNG")
    return path

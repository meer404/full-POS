"""Shared visual style for the whole application: palette, QSS, fonts, RTL, icons, shadows.

This is the single place styling lives — screens should reuse `Colors`, `icon()`, and
`apply_card_shadow()` rather than hardcoding colors or building qtawesome icons directly.
"""
from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

APP_FONT_FAMILY = "Segoe UI"
BASE_FONT_SIZE = 11


class Colors:
    BG = "#F7F8FA"
    SURFACE = "#FFFFFF"

    PRIMARY = "#2E7D32"
    PRIMARY_HOVER = "#256B29"
    PRIMARY_PRESSED = "#1E5722"
    PRIMARY_TINT = "#E9F5EA"

    SECONDARY = "#1565C0"
    SECONDARY_HOVER = "#11539F"
    SECONDARY_TINT = "#E8F0FB"

    WARNING = "#F9A825"
    WARNING_BG = "#FEF3D9"

    DANGER = "#C62828"
    DANGER_HOVER = "#A82121"
    DANGER_BG = "#FBEAEA"

    TEXT_PRIMARY = "#1A1A1A"
    TEXT_SECONDARY = "#6B7280"
    TEXT_ON_ACCENT = "#FFFFFF"

    BORDER = "#E5E7EB"
    ROW_ALT = "#FAFAFA"
    ROW_HOVER = "#F0F4F8"


FONT_STACK = "'Vazirmatn', 'Noto Sans Arabic', 'Segoe UI', Tahoma, sans-serif"


def icon(name: str, color: str = Colors.TEXT_SECONDARY):
    """Fetch a qtawesome icon with a consistent color, e.g. icon('fa5s.box', Colors.PRIMARY)."""
    return qta.icon(name, color=color)


def apply_card_shadow(widget: QWidget, blur: int = 24, y_offset: int = 3, alpha: int = 35):
    """Attach a soft drop shadow to a 'card' container (QGroupBox/QFrame), since QSS alone
    can't express box-shadow."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)
    return effect


STYLESHEET = f"""
* {{
    font-family: {FONT_STACK};
    font-size: 13px;
}}
QWidget {{
    background-color: {Colors.BG};
    color: {Colors.TEXT_PRIMARY};
}}
QMainWindow, QDialog {{
    background-color: {Colors.BG};
}}

/* ---- Buttons ---- */
QPushButton {{
    background-color: {Colors.PRIMARY};
    color: {Colors.TEXT_ON_ACCENT};
    border: none;
    border-radius: 9px;
    padding: 10px 20px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}
QPushButton:pressed {{ background-color: {Colors.PRIMARY_PRESSED}; }}
QPushButton:disabled {{ background-color: #BFC9D6; color: #F1F3F6; }}

QPushButton[danger="true"] {{ background-color: {Colors.DANGER}; }}
QPushButton[danger="true"]:hover {{ background-color: {Colors.DANGER_HOVER}; }}

QPushButton[secondary="true"] {{
    background-color: transparent;
    color: {Colors.TEXT_SECONDARY};
    border: 1.5px solid {Colors.BORDER};
}}
QPushButton[secondary="true"]:hover {{
    background-color: {Colors.ROW_HOVER};
    color: {Colors.TEXT_PRIMARY};
    border-color: {Colors.TEXT_SECONDARY};
}}
QPushButton[secondary="true"]:pressed {{ background-color: {Colors.BORDER}; }}

/* ---- Inputs ---- */
QLineEdit, QComboBox, QDateEdit, QSpinBox {{
    background-color: {Colors.SURFACE};
    border: 1.5px solid {Colors.BORDER};
    border-radius: 9px;
    padding: 9px 12px;
    min-height: 22px;
    selection-background-color: {Colors.SECONDARY_TINT};
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus {{
    border: 1.5px solid {Colors.SECONDARY};
}}
QLineEdit#barcodeInput {{
    font-size: 16px;
    font-weight: 600;
    padding: 14px 16px;
    border-radius: 10px;
    border: 2px solid {Colors.BORDER};
}}
QLineEdit#barcodeInput:focus {{
    border: 2px solid {Colors.PRIMARY};
}}

/* ---- Cards (QGroupBox used as a section card) ---- */
QGroupBox {{
    background-color: {Colors.SURFACE};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    margin-top: 14px;
    padding: 16px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 2px 8px;
    left: -8px;
    color: {Colors.TEXT_PRIMARY};
    font-size: 15px;
    font-weight: 600;
}}

QFrame#card {{
    background-color: {Colors.SURFACE};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
}}
QFrame#totalCard {{
    background-color: {Colors.PRIMARY_TINT};
    border: 1px solid {Colors.PRIMARY};
    border-radius: 12px;
}}
QFrame#loginCard {{
    background-color: {Colors.SURFACE};
    border-radius: 16px;
}}

/* ---- Tables ---- */
QTableWidget {{
    background-color: {Colors.SURFACE};
    alternate-background-color: {Colors.ROW_ALT};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    gridline-color: transparent;
    selection-background-color: {Colors.SECONDARY_TINT};
    selection-color: {Colors.TEXT_PRIMARY};
}}
QTableWidget::item {{
    padding: 6px;
    border-bottom: 1px solid {Colors.BORDER};
}}
QTableWidget::item:hover {{
    background-color: {Colors.ROW_HOVER};
}}
QHeaderView::section {{
    background-color: #F1F3F6;
    color: {Colors.TEXT_SECONDARY};
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid {Colors.BORDER};
    font-weight: 700;
}}
QListWidget {{
    background-color: {Colors.SURFACE};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 8px;
    border-radius: 6px;
}}
QListWidget::item:hover {{ background-color: {Colors.ROW_HOVER}; }}
QListWidget::item:selected {{ background-color: {Colors.SECONDARY_TINT}; color: {Colors.TEXT_PRIMARY}; }}

/* ---- Tabs ---- */
QTabWidget::pane {{
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    background: {Colors.BG};
    top: -1px;
}}
QTabBar::tab {{
    background: {Colors.SURFACE};
    color: {Colors.TEXT_SECONDARY};
    padding: 10px 20px;
    margin: 3px;
    border-radius: 9px;
    font-weight: 600;
    border: 1px solid {Colors.BORDER};
}}
QTabBar::tab:selected {{
    background: {Colors.SECONDARY};
    color: {Colors.TEXT_ON_ACCENT};
    border: 1px solid {Colors.SECONDARY};
}}
QTabBar::tab:hover:!selected {{
    background: {Colors.ROW_HOVER};
}}

/* ---- Labels (role-based type scale) ---- */
QLabel[role="title"] {{
    font-size: 20px;
    font-weight: 700;
    color: {Colors.TEXT_PRIMARY};
}}
QLabel[role="section"] {{
    font-size: 15px;
    font-weight: 600;
    color: {Colors.TEXT_PRIMARY};
}}
QLabel[role="total"] {{
    font-size: 22px;
    font-weight: 800;
    color: {Colors.PRIMARY};
}}
QLabel[role="grandtotal"] {{
    font-size: 32px;
    font-weight: 800;
    color: {Colors.PRIMARY};
}}
QLabel[role="error"] {{
    color: {Colors.DANGER};
    font-weight: 600;
}}
QLabel[role="warning"] {{
    color: {Colors.WARNING};
    font-weight: 700;
}}
QLabel[role="caption"] {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 12px;
}}

QCheckBox {{ spacing: 8px; }}
"""


def apply_app_style(app):
    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet(STYLESHEET)
    app.setFont(QFont(APP_FONT_FAMILY, BASE_FONT_SIZE))

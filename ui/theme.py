"""Design tokens + stylesheet loader for the whole application.

Single source of truth for colors, spacing, radii, and fonts. `ui/style.qss` holds the actual
QSS rules as `${TOKEN}` placeholders; `apply_app_style()` substitutes them from `Colors` /
`Spacing` / `Radius` below and applies the result. Screens/widgets should reuse `Colors`,
`Spacing`, `icon()`, and `apply_card_shadow()` here rather than hardcoding colors or sizes.
"""
from __future__ import annotations

from pathlib import Path
from string import Template

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

APP_FONT_FAMILY = "Segoe UI"
BASE_FONT_SIZE = 11

FONT_STACK = "'Vazirmatn', 'Noto Sans Arabic', 'Segoe UI', Tahoma, sans-serif"


def _gradient(top: str, bottom: str, angle: str = "x1:0, y1:0, x2:0, y2:1") -> str:
    """A vertical Qt-stylesheet gradient string, e.g. for bold button/card fills."""
    return f"qlineargradient({angle}, stop:0 {top}, stop:1 {bottom})"


class Colors:
    # ---- Surfaces ----
    BG = "#F5F7FA"
    SURFACE = "#FFFFFF"
    SURFACE_ALT = "#F1F4F9"

    # ---- Brand / primary (vivid green) ----
    PRIMARY_LIGHT = "#22C55E"
    PRIMARY = "#16A34A"
    PRIMARY_HOVER = "#128A3E"
    PRIMARY_PRESSED = "#0F7A37"
    PRIMARY_TINT = "#E3F9EC"
    BRAND = PRIMARY
    BRAND_HOVER = PRIMARY_HOVER
    BRAND_LIGHT = PRIMARY_TINT

    # ---- Secondary / info (vivid blue) ----
    SECONDARY_LIGHT = "#3B82F6"
    SECONDARY = "#2563EB"
    SECONDARY_HOVER = "#1D4ED8"
    SECONDARY_TINT = "#E5EEFF"
    INFO = SECONDARY
    INFO_BG = SECONDARY_TINT

    # ---- Semantic ----
    SUCCESS = PRIMARY
    SUCCESS_BG = PRIMARY_TINT

    WARNING_LIGHT = "#FBBF24"
    WARNING = "#F59E0B"
    WARNING_HOVER = "#D97706"
    WARNING_BG = "#FEF3D9"
    WARNING_BG_HOVER = "#FCE1A8"

    DANGER_LIGHT = "#F87171"
    DANGER = "#EF4444"
    DANGER_HOVER = "#DC2626"
    DANGER_BG = "#FDE8E8"
    DANGER_BG_HOVER = "#FBD0D0"

    # ---- Role badges (Users screen) ----
    ROLE_ADMIN_LIGHT = "#A78BFA"
    ROLE_ADMIN = "#8B5CF6"
    ROLE_ADMIN_BG = "#F1EAFE"
    ROLE_CASHIER = SECONDARY
    ROLE_CASHIER_BG = SECONDARY_TINT

    # ---- Text ----
    TEXT_PRIMARY = "#111827"
    TEXT_SECONDARY = "#6B7280"
    TEXT_ON_ACCENT = "#FFFFFF"
    TEXT = TEXT_PRIMARY
    TEXT_MUTED = TEXT_SECONDARY

    # ---- Borders / rows ----
    BORDER = "#E5E7EB"
    BORDER_STRONG = "#CBD5E1"
    ROW_ALT = "#FAFAFA"
    ROW_HOVER = "#F0F4F8"

    # ---- Gradients (bold accents: buttons, totals, KPI tiles, active nav) ----
    GRADIENT_PRIMARY = _gradient(PRIMARY_LIGHT, PRIMARY)
    GRADIENT_PRIMARY_HOVER = _gradient(PRIMARY, PRIMARY_HOVER)
    GRADIENT_SECONDARY = _gradient(SECONDARY_LIGHT, SECONDARY)
    GRADIENT_WARNING = _gradient(WARNING_LIGHT, WARNING)
    GRADIENT_DANGER = _gradient(DANGER_LIGHT, DANGER)
    GRADIENT_DANGER_HOVER = _gradient(DANGER, DANGER_HOVER)
    GRADIENT_ADMIN = _gradient(ROLE_ADMIN_LIGHT, ROLE_ADMIN)
    GRADIENT_TOTAL = _gradient("#ECFDF5", PRIMARY_TINT, "x1:0, y1:0, x2:1, y2:0")


class Spacing:
    """The only spacing values allowed anywhere in the UI."""
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


class Radius:
    INPUT = 8
    CARD = 12
    PILL = 999


def icon(name: str, color: str = Colors.TEXT_SECONDARY):
    """Fetch a qtawesome icon with a consistent color, e.g. icon('fa5s.box', Colors.PRIMARY)."""
    return qta.icon(name, color=color)


def apply_card_shadow(widget: QWidget, blur: int = 24, y_offset: int = 3, alpha: int = 35):
    """Attach a soft drop shadow to a 'card' container (QFrame/QGroupBox), since QSS alone
    can't express box-shadow."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)
    return effect


def _tokens() -> dict:
    tokens = {k: v for k, v in vars(Colors).items() if not k.startswith("_")}
    tokens.update({f"SPACE_{k}": v for k, v in vars(Spacing).items() if not k.startswith("_")})
    tokens.update({f"RADIUS_{k}": v for k, v in vars(Radius).items() if not k.startswith("_")})
    tokens["FONT_STACK"] = FONT_STACK
    return tokens


def load_stylesheet() -> str:
    qss_path = Path(__file__).with_name("style.qss")
    template = Template(qss_path.read_text(encoding="utf-8"))
    return template.substitute(_tokens())


def apply_app_style(app):
    from ui.widgets.motion import install_button_feedback

    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet(load_stylesheet())
    app.setFont(QFont(APP_FONT_FAMILY, BASE_FONT_SIZE))
    app._button_feedback = install_button_feedback(app)

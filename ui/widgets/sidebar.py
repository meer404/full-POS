"""Sidebar navigation shown on the right edge of the main window (RTL).

Pure UI chrome: no DB access, no business logic. `MainWindow` decides which (icon, label)
pairs exist based on `user.is_admin` and passes them in here, along with the logged-in user's
display info and a logout callback (kept as `MainWindow.close`, same as before — this widget
does not implement session switching).
"""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ui.theme import Colors, icon
from ui.widgets.motion import animate_slide


class Sidebar(QFrame):
    navigationChanged = Signal(int)

    def __init__(
        self,
        items: list[tuple[str, str]],
        username: str = "",
        role: str = "",
        on_logout=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(232)

        self._buttons: list[QPushButton] = []
        self._indicator_anim = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_brand())

        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, (icon_name, label) in enumerate(items):
            btn = QPushButton(f"  {label}")
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setIconSize(QSize(18, 18))
            btn.setIcon(icon(icon_name, Colors.TEXT_SECONDARY))
            btn.toggled.connect(
                lambda checked, b=btn, n=icon_name: b.setIcon(
                    icon(n, Colors.PRIMARY if checked else Colors.TEXT_SECONDARY)
                )
            )
            btn.clicked.connect(lambda _, i=index: self.navigationChanged.emit(i))
            btn.clicked.connect(lambda _, i=index: self._animate_indicator_to(i))
            group.addButton(btn)
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()
        layout.addWidget(self._build_user_card(username, role, on_logout))

        # A thin bar that slides to the active nav button — floats above the layout, so its
        # geometry can be animated independently of it.
        self._indicator = QFrame(self)
        self._indicator.setObjectName("sidebarIndicator")
        self._indicator.hide()

        if self._buttons:
            self._buttons[0].setChecked(True)
            QTimer.singleShot(0, lambda: self._place_indicator(0, animated=False))

    def _place_indicator(self, index: int, animated: bool = True):
        btn = self._buttons[index]
        target = QRect(self.width() - 4, btn.y(), 4, btn.height())
        if not animated or not self._indicator.isVisible():
            self._indicator.setGeometry(target)
            self._indicator.show()
            self._indicator.raise_()
            return
        self._indicator_anim = animate_slide(self._indicator, self._indicator.geometry(), target)

    def _animate_indicator_to(self, index: int):
        self._place_indicator(index, animated=True)

    def _build_brand(self) -> QFrame:
        brand = QFrame()
        brand.setObjectName("sidebarBrand")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(18, 18, 18, 18)
        brand_layout.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(icon("fa5s.cash-register", Colors.PRIMARY).pixmap(QSize(22, 22)))
        brand_layout.addWidget(logo)

        brand_label = QLabel("خەزنە")
        brand_label.setProperty("role", "section")
        brand_layout.addWidget(brand_label)
        brand_layout.addStretch()
        return brand

    def _build_user_card(self, username: str, role: str, on_logout) -> QFrame:
        card = QFrame()
        card.setObjectName("sidebarUserCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        info_row = QHBoxLayout()
        info_row.setSpacing(10)

        avatar = QLabel((username[:1] or "?").upper())
        avatar.setObjectName("sidebarAvatar")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        info_row.addWidget(avatar)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        name_label = QLabel(username)
        name_label.setProperty("role", "section")
        role_label = QLabel(role)
        role_label.setProperty("role", "caption")
        text_col.addWidget(name_label)
        text_col.addWidget(role_label)
        info_row.addLayout(text_col)
        info_row.addStretch()
        layout.addLayout(info_row)

        logout_btn = QPushButton(" چوونەدەرەوە")
        logout_btn.setIcon(icon("fa5s.sign-out-alt", Colors.TEXT_SECONDARY))
        logout_btn.setProperty("secondary", True)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setToolTip("داخستنی سیستەم")
        if on_logout:
            logout_btn.clicked.connect(on_logout)
        layout.addWidget(logout_btn)

        return card

    def setCurrentIndex(self, index: int):
        self._buttons[index].setChecked(True)
        self._animate_indicator_to(index)

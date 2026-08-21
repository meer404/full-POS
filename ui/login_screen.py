"""Login dialog shown before the main window opens."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

import auth
from ui.style import Colors, apply_card_shadow, icon


class LoginScreen(QDialog):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.user: auth.User | None = None

        self.setWindowTitle("چوونەژوورەوە - سیستەمی فرۆشتن")
        self.resize(900, 600)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet(f"QDialog {{ background-color: {Colors.BG}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()

        center_row = QHBoxLayout()
        center_row.addStretch()

        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(380)
        apply_card_shadow(card, blur=36, y_offset=6, alpha=45)

        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(36, 40, 36, 36)

        logo_label = QLabel()
        logo_label.setPixmap(icon("fa5s.cash-register", Colors.PRIMARY).pixmap(QSize(56, 56)))
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        title = QLabel("سیستەمی خەزنە / فرۆشتن")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("بۆ بەردەوامبوون بچۆرەژوورەوە")
        subtitle.setProperty("role", "caption")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        layout.addWidget(QLabel("ناوی بەکارهێنەر"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("ناوی بەکارهێنەر بنووسە")
        self.username_input.setMinimumHeight(40)
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("وشەی نهێنی"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("وشەی نهێنی بنووسە")
        self.password_input.setMinimumHeight(40)
        layout.addWidget(self.password_input)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        layout.addSpacing(4)

        self.login_button = QPushButton("چوونەژوورەوە")
        self.login_button.setMinimumHeight(44)
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self.attempt_login)
        layout.addWidget(self.login_button)

        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.attempt_login)

        center_row.addWidget(card)
        center_row.addStretch()
        outer.addLayout(center_row)
        outer.addStretch()

        self.username_input.setFocus()

    def attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.error_label.setText("تکایە ناو و وشەی نهێنی پڕبکەوە")
            return

        user = auth.login(self.conn, username, password)
        if user is None:
            self.error_label.setText("ناو یان وشەی نهێنی هەڵەیە")
            self.password_input.clear()
            self.password_input.setFocus()
            return

        self.user = user
        self.accept()

"""Login dialog shown before the main window opens."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

import auth


class LoginScreen(QDialog):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.user: auth.User | None = None

        self.setWindowTitle("چوونەژوورەوە - سیستەمی فرۆشتن")
        self.setFixedSize(360, 320)
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("سیستەمی خەزنە / فرۆشتن")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(10)

        layout.addWidget(QLabel("ناوی بەکارهێنەر:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("ناوی بەکارهێنەر بنووسە")
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("وشەی نهێنی:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("وشەی نهێنی بنووسە")
        layout.addWidget(self.password_input)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)

        self.login_button = QPushButton("چوونەژوورەوە")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self.attempt_login)
        layout.addWidget(self.login_button)

        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.attempt_login)

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

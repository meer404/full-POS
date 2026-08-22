"""Entry point: login -> main window with role-based tabs -> backup on close."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import auth
import backup
import database
from ui.theme import apply_app_style
from ui.pages.login_page import LoginScreen
from ui.pages.products_page import ProductEntryScreen
from ui.pages.sales_page import SalesScreen
from ui.pages.reports_page import ReportsScreen
from ui.pages.expiry_page import ExpiryScreen
from ui.pages.users_page import UsersScreen
from ui.widgets.sidebar import Sidebar
from ui.widgets.topbar import TopBar


class MainWindow(QMainWindow):
    def __init__(self, conn, user: auth.User):
        super().__init__()
        self.conn = conn
        self.user = user

        self.setWindowTitle(f"سیستەمی خەزنە / فرۆشتن — {user.username} ({user.role})")
        self.resize(1200, 750)
        self.setLayoutDirection(Qt.RightToLeft)

        # (icon_name, label, widget) — every role gets Sales + Product Entry;
        # Reports/Expiry/Users are admin-only, same gating as before (just sidebar now, not tabs).
        nav_items: list[tuple[str, str, QWidget]] = [
            ("fa5s.shopping-cart", "فرۆشتن", SalesScreen(conn, user)),
            ("fa5s.box", "زیادکردنی بەرهەم", ProductEntryScreen(conn, user)),
        ]
        if user.is_admin:
            nav_items += [
                ("fa5s.chart-bar", "ڕاپۆرت", ReportsScreen(conn)),
                ("fa5s.exclamation-triangle", "بەسەرچوونی بەرهەم", ExpiryScreen(conn)),
                ("fa5s.users", "بەڕێوەبردنی بەکارهێنەران", UsersScreen(conn, user)),
            ]
        self._page_titles = [label for _, label, _ in nav_items]

        self.stack = QStackedWidget()
        for _, _, widget in nav_items:
            self.stack.addWidget(widget)

        self.sidebar = Sidebar(
            [(name, label) for name, label, _ in nav_items],
            username=user.username,
            role=user.role,
            on_logout=self.close,
        )
        self.sidebar.navigationChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.navigationChanged.connect(self._on_nav_changed)

        self.topbar = TopBar()

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.topbar)
        content_layout.addWidget(self.stack, 1)

        shell = QWidget()
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        shell_layout.addWidget(self.sidebar)
        shell_layout.addWidget(content, 1)
        self.setCentralWidget(shell)

        self._on_nav_changed(0)

    def _on_nav_changed(self, index: int):
        self.topbar.set_title(self._page_titles[index])

    def closeEvent(self, event):
        try:
            self.conn.commit()
            self.conn.close()
        finally:
            backup.create_backup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    apply_app_style(app)

    conn = database.init_db()

    login = LoginScreen(conn)
    if login.exec() != LoginScreen.Accepted or login.user is None:
        sys.exit(0)

    window = MainWindow(conn, login.user)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

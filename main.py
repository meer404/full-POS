"""Entry point: login -> main window with role-based tabs -> backup on close."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

import auth
import backup
import database
from ui.style import apply_app_style
from ui.login_screen import LoginScreen
from ui.product_entry import ProductEntryScreen
from ui.sales_screen import SalesScreen
from ui.reports_screen import ReportsScreen
from ui.expiry_screen import ExpiryScreen
from ui.users_screen import UsersScreen


class MainWindow(QMainWindow):
    def __init__(self, conn, user: auth.User):
        super().__init__()
        self.conn = conn
        self.user = user

        self.setWindowTitle(f"سیستەمی خەزنە / فرۆشتن — {user.username} ({user.role})")
        self.resize(1100, 700)
        self.setLayoutDirection(Qt.RightToLeft)

        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        # Every role can sell and enter/restock products.
        tabs.addTab(SalesScreen(conn, user), "فرۆشتن")
        tabs.addTab(ProductEntryScreen(conn, user), "زیادکردنی بەرهەم")

        # Admin-only tabs.
        if user.is_admin:
            tabs.addTab(ReportsScreen(conn), "ڕاپۆرت")
            tabs.addTab(ExpiryScreen(conn), "بەسەرچوونی بەرهەم")
            tabs.addTab(UsersScreen(conn, user), "بەڕێوەبردنی بەکارهێنەران")

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

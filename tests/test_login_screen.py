"""Headless GUI test for ui/login_screen.py.

Run with: QT_QPA_PLATFORM=offscreen python tests/test_login_screen.py
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

import database
from ui.pages.login_page import LoginScreen


def run():
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_pos.db"
        conn = database.init_db(db_path)

        # Wrong credentials
        screen = LoginScreen(conn)
        screen.username_input.setText("admin")
        screen.password_input.setText("wrong")
        screen.attempt_login()
        assert screen.user is None
        assert screen.error_label.text() != ""
        print("OK: wrong password shows error, dialog stays open")

        # Correct credentials
        screen2 = LoginScreen(conn)
        screen2.username_input.setText("admin")
        screen2.password_input.setText("admin123")
        screen2.attempt_login()
        assert screen2.user is not None
        assert screen2.user.username == "admin"
        assert screen2.user.role == "admin"
        print("OK: correct credentials accepted, user role captured")

        # Empty fields
        screen3 = LoginScreen(conn)
        screen3.attempt_login()
        assert screen3.user is None
        assert "پڕ" in screen3.error_label.text() or screen3.error_label.text() != ""
        print("OK: empty fields rejected with message")

        conn.close()

    print("\nAll login screen tests passed.")


if __name__ == "__main__":
    run()

"""Headless GUI test for ui/users_screen.py.

Run with: QT_QPA_PLATFORM=offscreen python tests/test_users_screen.py
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

import auth
import database
from ui.pages.users_page import UsersScreen


def run():
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_pos.db"
        conn = database.init_db(db_path)
        admin = auth.login(conn, "admin", "admin123")

        screen = UsersScreen(conn, admin)
        assert screen.table.rowCount() == 1  # just the seeded admin
        print("OK: initial table shows only the seeded admin")

        # --- Add a cashier ---
        assert screen.add_user("cashier1", "pass123", "cashier") is True
        screen.refresh_table()
        assert screen.table.rowCount() == 2
        cashier_login = auth.login(conn, "cashier1", "pass123")
        assert cashier_login is not None and cashier_login.role == "cashier"
        print("OK: add_user creates a working cashier account")

        # --- Duplicate username rejected ---
        assert screen.add_user("cashier1", "other", "cashier") is False
        assert "بەکارهێنراوە" in screen.error_label.text()
        print("OK: duplicate username rejected with Kurdish error")

        # --- Change password ---
        cashier_id = conn.execute("SELECT id FROM users WHERE username='cashier1'").fetchone()["id"]
        assert screen.change_password(cashier_id, "newpass456") is True
        assert auth.login(conn, "cashier1", "pass123") is None
        assert auth.login(conn, "cashier1", "newpass456") is not None
        print("OK: change_password updates credentials correctly")

        # --- Cannot remove yourself ---
        assert screen.remove_user(admin.id) is False
        assert "خۆت" in screen.error_label.text()
        print("OK: admin cannot delete their own account")

        # --- Remove the cashier ---
        assert screen.remove_user(cashier_id) is True
        screen.refresh_table()
        assert screen.table.rowCount() == 1
        assert auth.login(conn, "cashier1", "newpass456") is None
        print("OK: remove_user deletes the target user")

        conn.close()

    print("\nAll users screen tests passed.")


if __name__ == "__main__":
    run()

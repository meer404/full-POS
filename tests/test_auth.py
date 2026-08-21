"""Headless test for auth.py — run directly with `python tests/test_auth.py`."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database
import auth


def run():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_pos.db"
        conn = database.init_db(db_path)

        user = auth.login(conn, "admin", "admin123")
        assert user is not None and user.role == "admin" and user.is_admin
        print("OK: default admin can log in")

        assert auth.login(conn, "admin", "wrongpass") is None
        print("OK: wrong password rejected")

        assert auth.login(conn, "nosuchuser", "admin123") is None
        print("OK: unknown username rejected")

        uid = auth.create_user(conn, "cashier1", "pass123", "cashier")
        cashier = auth.login(conn, "cashier1", "pass123")
        assert cashier is not None and cashier.role == "cashier" and not cashier.is_admin
        print("OK: new cashier created and can log in, is_admin is False")

        auth.change_password(conn, uid, "newpass456")
        assert auth.login(conn, "cashier1", "pass123") is None
        assert auth.login(conn, "cashier1", "newpass456") is not None
        print("OK: change_password invalidates old password, accepts new one")

        users = auth.list_users(conn)
        assert len(users) == 2
        print("OK: list_users returns both users")

        auth.delete_user(conn, uid)
        assert auth.login(conn, "cashier1", "newpass456") is None
        assert len(auth.list_users(conn)) == 1
        print("OK: delete_user removes the user")

        conn.close()

    print("\nAll auth tests passed.")


if __name__ == "__main__":
    run()

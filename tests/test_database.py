"""Headless test for database.py — run directly with `python tests/test_database.py`."""
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database


def run():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_pos.db"
        conn = database.init_db(db_path)

        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        expected = {"users", "products", "stock_batches", "sales", "sale_items", "returns"}
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"
        print("OK: all tables created:", sorted(expected))

        admin = conn.execute(
            "SELECT * FROM users WHERE username=?", (database.DEFAULT_ADMIN_USERNAME,)
        ).fetchone()
        assert admin is not None
        assert admin["role"] == "admin"
        assert admin["password_hash"] == database.hash_password(database.DEFAULT_ADMIN_PASSWORD)
        print("OK: default admin seeded with correct sha256 hash")

        conn2 = database.init_db(db_path)
        count = conn2.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        assert count == 1, "init_db must not duplicate the seeded admin on re-run"
        print("OK: init_db is idempotent (no duplicate admin)")

        conn.execute(
            "INSERT INTO products (name, barcode, category, sale_price) VALUES (?,?,?,?)",
            ("Milk", "1234567890123", "Dairy", 1000),
        )
        conn.commit()
        pid = conn.execute("SELECT id FROM products WHERE barcode='1234567890123'").fetchone()["id"]

        conn.execute(
            "INSERT INTO stock_batches (product_id, purchase_price, quantity, initial_quantity, expiry_date) "
            "VALUES (?,?,?,?,?)",
            (pid, 700, 50, 50, "2026-12-01"),
        )
        conn.commit()

        try:
            conn.execute(
                "INSERT INTO products (name, barcode, category, sale_price) VALUES (?,?,?,?)",
                ("Milk2", "1234567890123", "Dairy", 1200),
            )
            conn.commit()
            raise AssertionError("Expected UNIQUE constraint violation on duplicate barcode")
        except sqlite3.IntegrityError:
            print("OK: duplicate barcode rejected (UNIQUE constraint enforced)")

        conn.close()
        conn2.close()

    print("\nAll database tests passed.")


if __name__ == "__main__":
    run()

"""Headless GUI test for ui/expiry_screen.py.

Run with: QT_QPA_PLATFORM=offscreen python tests/test_expiry_screen.py
"""
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

import database
import models
from ui.expiry_screen import ExpiryScreen


def run():
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_pos.db"
        conn = database.init_db(db_path)

        today = date.today()
        expired_date = (today - timedelta(days=2)).isoformat()
        soon_date = (today + timedelta(days=3)).isoformat()
        far_date = (today + timedelta(days=60)).isoformat()

        pid1 = models.create_product(conn, "Yogurt", "1111111111111", "Dairy", 800, min_stock=5)
        expired_batch = models.add_stock_batch(conn, pid1, purchase_price=500, quantity=10, expiry_date=expired_date)

        pid2 = models.create_product(conn, "Juice", "2222222222222", "Drinks", 1200, min_stock=5)
        soon_batch = models.add_stock_batch(conn, pid2, purchase_price=800, quantity=6, expiry_date=soon_date)

        pid3 = models.create_product(conn, "Rice", "3333333333333", "Grains", 3000, min_stock=5)
        models.add_stock_batch(conn, pid3, purchase_price=2000, quantity=40, expiry_date=far_date)

        screen = ExpiryScreen(conn)

        assert screen.expired_table.rowCount() == 1
        assert screen.expired_table.item(0, 0).text() == "Yogurt"
        print("OK: expired table shows only the expired batch (Yogurt)")

        assert screen.warning_table.rowCount() == 1
        assert screen.warning_table.item(0, 0).text() == "Juice"
        from PySide6.QtGui import QColor
        assert screen.warning_table.item(0, 0).background().color() == QColor("#fff3cd")
        print("OK: warning table shows Juice (expiring in 3 days), highlighted yellow")

        # --- Mark expired batch as loss ---
        screen.mark_as_loss(expired_batch)
        batch_row = conn.execute("SELECT * FROM stock_batches WHERE id=?", (expired_batch,)).fetchone()
        assert batch_row["status"] == "disposed" and batch_row["quantity"] == 0
        assert screen.expired_table.rowCount() == 0
        print("OK: mark_as_loss disposes the batch and the table refreshes to empty")

        # --- Return the soon-expiring batch to supplier ---
        screen.return_to_supplier(soon_batch)
        ret = conn.execute("SELECT * FROM returns WHERE batch_id=?", (soon_batch,)).fetchone()
        assert ret["reason"] == "supplier_return"
        assert screen.warning_table.rowCount() == 0
        print("OK: return_to_supplier disposes the batch and logs reason correctly")

        conn.close()

    print("\nAll expiry screen tests passed.")


if __name__ == "__main__":
    run()

"""Headless GUI test for ui/reports_screen.py.

Run with: QT_QPA_PLATFORM=offscreen python tests/test_reports_screen.py
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

import database
import models
from ui.pages.reports_page import ReportsScreen, PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY


def run():
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_pos.db"
        conn = database.init_db(db_path)
        admin_id = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()["id"]

        pid = models.create_product(conn, "Milk", "1111111111111", "Dairy", 1000, min_stock=5)
        models.add_stock_batch(conn, pid, purchase_price=700, quantity=100, expiry_date=None)
        sale_id = models.complete_sale(
            conn,
            cart_items=[{"product_id": pid, "quantity": 10, "unit_price": 1000}],
            discount=0,
            cashier_id=admin_id,
        )
        # sales.created_at defaults to UTC (SQLite CURRENT_TIMESTAMP) but the screen filters
        # by local date (QDate::currentDate()); pin it to local "now" so this test isn't
        # flaky within a few hours of local midnight. This is a test-only adjustment — see
        # the UTC/local mismatch noted for models.py/database.py separately.
        conn.execute("UPDATE sales SET created_at = datetime('now', 'localtime') WHERE id = ?", (sale_id,))
        conn.commit()

        screen = ReportsScreen(conn)

        assert screen.current_period() == PERIOD_DAILY
        assert screen.receipt_stat.value_label.text() == "1"
        assert screen.qty_stat.value_label.text() == "10"
        assert screen.top_table.rowCount() == 1
        print("OK: default daily view shows today's single sale with correct totals")

        screen.set_period(PERIOD_WEEKLY)
        assert screen.receipt_stat.value_label.text() == "1"
        print("OK: switching to weekly period auto-refreshes and still shows the sale")

        screen.set_period(PERIOD_MONTHLY)
        assert screen.receipt_stat.value_label.text() == "1"
        print("OK: switching to monthly period works")

        conn.close()

    print("\nAll reports screen tests passed.")


if __name__ == "__main__":
    run()

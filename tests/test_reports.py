"""Headless test for models.sales_report — run with `python tests/test_reports.py`."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database
import models


def run():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_pos.db"
        conn = database.init_db(db_path)
        admin_id = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()["id"]

        milk_id = models.create_product(conn, "Milk", "1111111111111", "Dairy", 1000, min_stock=5)
        models.add_stock_batch(conn, milk_id, purchase_price=700, quantity=100, expiry_date=None)
        bread_id = models.create_product(conn, "Bread", "2222222222222", "Bakery", 500, min_stock=5)
        models.add_stock_batch(conn, bread_id, purchase_price=300, quantity=100, expiry_date=None)

        # Sale "today"
        s1 = models.complete_sale(
            conn,
            cart_items=[
                {"product_id": milk_id, "quantity": 10, "unit_price": 1000},
                {"product_id": bread_id, "quantity": 4, "unit_price": 500},
            ],
            discount=500,
            cashier_id=admin_id,
        )

        # Backdate a second sale to yesterday to test date filtering
        s2 = models.complete_sale(
            conn,
            cart_items=[{"product_id": milk_id, "quantity": 20, "unit_price": 1000}],
            discount=0,
            cashier_id=admin_id,
        )
        conn.execute(
            "UPDATE sales SET created_at = datetime('now', '-1 day') WHERE id = ?", (s2,)
        )
        conn.commit()

        today = conn.execute("SELECT DATE('now') AS d").fetchone()["d"]

        report_today = models.sales_report(conn, today, today)
        assert report_today["receipt_count"] == 1, report_today
        assert report_today["total_qty"] == 14  # 10 milk + 4 bread
        assert report_today["total_revenue"] == 10 * 1000 + 4 * 500 - 500  # final_amount
        expected_profit = (1000 - 700) * 10 + (500 - 300) * 4
        assert report_today["total_profit"] == expected_profit
        print("OK: today-only report has correct receipt count, qty, revenue, profit")

        names = [p["name"] for p in report_today["top_products"]]
        assert names[0] == "Milk"  # 10 units sold vs bread's 4
        print("OK: top products ranked by quantity sold:", report_today["top_products"])

        report_both = models.sales_report(conn, "2000-01-01", today)
        assert report_both["receipt_count"] == 2
        assert report_both["total_qty"] == 34  # 10+4+20
        print("OK: wider date range picks up both sales (2 receipts, 34 items)")

        conn.close()

    print("\nAll reports tests passed.")


if __name__ == "__main__":
    run()

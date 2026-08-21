"""Headless test for FIFO sale-completion logic in models.complete_sale."""
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

        pid = models.create_product(conn, "Milk", "1111111111111", "Dairy", 1000, min_stock=5)
        # Batch A: nearest expiry, 10 units @ 700
        batch_a = models.add_stock_batch(conn, pid, purchase_price=700, quantity=10, expiry_date="2026-01-01")
        # Batch B: later expiry, 20 units @ 850
        batch_b = models.add_stock_batch(conn, pid, purchase_price=850, quantity=20, expiry_date="2026-06-01")

        # Sell 15 units -> should take all 10 from batch A, then 5 from batch B (split across batches)
        sale_id = models.complete_sale(
            conn,
            cart_items=[{"product_id": pid, "quantity": 15, "unit_price": 1000}],
            discount=0,
            cashier_id=admin_id,
        )
        assert sale_id is not None
        print("OK: sale completed, id =", sale_id)

        batch_a_row = conn.execute("SELECT * FROM stock_batches WHERE id=?", (batch_a,)).fetchone()
        batch_b_row = conn.execute("SELECT * FROM stock_batches WHERE id=?", (batch_b,)).fetchone()
        assert batch_a_row["quantity"] == 0, f"batch A should be fully depleted, got {batch_a_row['quantity']}"
        assert batch_b_row["quantity"] == 15, f"batch B should have 20-5=15 left, got {batch_b_row['quantity']}"
        print("OK: FIFO deduction — batch A (nearest expiry) fully depleted first (0 left)")
        print("OK: remainder correctly split into batch B (15 left, was 20)")

        items = conn.execute("SELECT * FROM sale_items WHERE sale_id=? ORDER BY batch_id", (sale_id,)).fetchall()
        assert len(items) == 2, f"expected 2 sale_item rows (one per batch consumed), got {len(items)}"
        qty_by_batch = {r["batch_id"]: r["quantity"] for r in items}
        assert qty_by_batch[batch_a] == 10
        assert qty_by_batch[batch_b] == 5
        print("OK: two sale_items rows created, one per (product, batch) combination, qty 10 + 5")

        sale = conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
        assert sale["total_amount"] == 15000
        assert sale["discount"] == 0
        assert sale["final_amount"] == 15000
        print("OK: sales row totals correct (15 x 1000 = 15,000 IQD)")

        # Sell remaining 15 units of batch B fully -> should deplete batch B exactly
        sale_id2 = models.complete_sale(
            conn,
            cart_items=[{"product_id": pid, "quantity": 15, "unit_price": 1000}],
            discount=2000,
            cashier_id=admin_id,
        )
        batch_b_row2 = conn.execute("SELECT * FROM stock_batches WHERE id=?", (batch_b,)).fetchone()
        assert batch_b_row2["quantity"] == 0
        sale2 = conn.execute("SELECT * FROM sales WHERE id=?", (sale_id2,)).fetchone()
        assert sale2["total_amount"] == 15000
        assert sale2["discount"] == 2000
        assert sale2["final_amount"] == 13000
        print("OK: discount applied correctly (15,000 - 2,000 = 13,000), batch B now empty")

        # Now stock is fully depleted -> selling 1 more must fail with InsufficientStockError
        # and must NOT create a sale row or partially deduct anything.
        sales_count_before = conn.execute("SELECT COUNT(*) c FROM sales").fetchone()["c"]
        try:
            models.complete_sale(
                conn,
                cart_items=[{"product_id": pid, "quantity": 1, "unit_price": 1000}],
                discount=0,
                cashier_id=admin_id,
            )
            raise AssertionError("Expected InsufficientStockError")
        except models.InsufficientStockError:
            print("OK: selling beyond available stock raises InsufficientStockError")

        sales_count_after = conn.execute("SELECT COUNT(*) c FROM sales").fetchone()["c"]
        assert sales_count_after == sales_count_before, "failed sale must not leave a partial sales row (rollback)"
        print("OK: failed sale rolled back cleanly, no stray sales row created")

        # Multi-product cart in a single sale, spanning fresh batches
        pid2 = models.create_product(conn, "Bread", "2222222222222", "Bakery", 500, min_stock=5)
        models.add_stock_batch(conn, pid2, purchase_price=300, quantity=8, expiry_date=None)
        sale_id3 = models.complete_sale(
            conn,
            cart_items=[{"product_id": pid2, "quantity": 3, "unit_price": 500}],
            discount=0,
            cashier_id=admin_id,
        )
        bread_batches = conn.execute("SELECT * FROM stock_batches WHERE product_id=?", (pid2,)).fetchall()
        assert bread_batches[0]["quantity"] == 5
        print("OK: independent product sale in a fresh sale transaction works correctly")

        conn.close()

    print("\nAll FIFO sale tests passed.")


if __name__ == "__main__":
    run()

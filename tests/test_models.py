"""Headless test for models.py — run with `python tests/test_models.py`."""
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

        # Local barcode generation
        bc1 = models.generate_local_barcode(conn)
        assert bc1.startswith("9") and len(bc1) == 13
        print("OK: generated local barcode is well-formed:", bc1)

        # New product + first batch
        pid = models.create_product(conn, "Milk", bc1, "Dairy", 1000, unit="دانە", min_stock=10)
        models.add_stock_batch(conn, pid, purchase_price=700, quantity=50, expiry_date="2026-12-01")
        assert models.get_total_stock(conn, pid) == 50
        assert models.get_nearest_expiry(conn, pid) == "2026-12-01"
        print("OK: new product created with first batch, stock/expiry correct")

        # Restock same product at a DIFFERENT price and expiry -> must create a second batch row, not update
        models.add_stock_batch(conn, pid, purchase_price=850, quantity=30, expiry_date="2026-06-01")
        batches = conn.execute(
            "SELECT * FROM stock_batches WHERE product_id=? ORDER BY id", (pid,)
        ).fetchall()
        assert len(batches) == 2, f"Expected 2 separate batches, got {len(batches)}"
        assert batches[0]["purchase_price"] == 700
        assert batches[1]["purchase_price"] == 850
        assert models.get_total_stock(conn, pid) == 80
        assert models.get_nearest_expiry(conn, pid) == "2026-06-01"
        print("OK: restock created a NEW batch row (2 batches), preserving different prices/expiries")
        print("OK: total stock sums both batches (80), nearest expiry is the earlier one")

        # FIFO ordering: nearest expiry first
        fifo = models.get_active_batches_fifo(conn, pid)
        assert fifo[0]["expiry_date"] == "2026-06-01"
        assert fifo[1]["expiry_date"] == "2026-12-01"
        print("OK: FIFO batch order is nearest-expiry-first")

        # Product lookup by barcode
        found = models.find_product_by_barcode(conn, bc1)
        assert found is not None and found["name"] == "Milk"
        print("OK: find_product_by_barcode works")

        # Duplicate barcode via generate_local_barcode must never collide
        bc2 = models.generate_local_barcode(conn)
        assert bc2 != bc1
        print("OK: second generated barcode differs from the first:", bc2)

        # Low stock detection
        pid2 = models.create_product(conn, "Bread", models.generate_local_barcode(conn), "Bakery", 500, min_stock=20)
        models.add_stock_batch(conn, pid2, purchase_price=300, quantity=5, expiry_date=None)
        low = models.list_low_stock_products(conn)
        low_names = {p["name"] for p in low}
        assert "Bread" in low_names
        assert "Milk" not in low_names
        print("OK: low stock list correctly flags Bread (5 < min 20), not Milk (80 >= 10)")

        # No-expiry batch should sort after dated batches, ordered by received_at
        models.add_stock_batch(conn, pid2, purchase_price=310, quantity=10, expiry_date=None)
        fifo2 = models.get_active_batches_fifo(conn, pid2)
        assert len(fifo2) == 2
        assert fifo2[0]["quantity"] == 5  # received first
        assert fifo2[1]["quantity"] == 10
        print("OK: batches with no expiry ordered by received_at (oldest first)")

        conn.close()

    print("\nAll model tests passed.")


if __name__ == "__main__":
    run()

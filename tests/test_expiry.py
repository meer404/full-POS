"""Headless test for expiry-related helpers in models.py."""
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database
import models


def run():
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

        today_str = today.isoformat()
        warn_str = (today + timedelta(days=7)).isoformat()

        expired = models.list_expired_batches(conn, today_str)
        assert len(expired) == 1
        assert expired[0]["id"] == expired_batch
        assert expired[0]["product_name"] == "Yogurt"
        print("OK: list_expired_batches finds only the already-expired batch")

        soon = models.list_expiring_soon_batches(conn, today_str, warn_str)
        assert len(soon) == 1
        assert soon[0]["id"] == soon_batch
        print("OK: list_expiring_soon_batches finds only the batch expiring within 7 days")

        # far_date batch (60 days out) must not appear in either list
        expired_ids = {b["id"] for b in expired}
        soon_ids = {b["id"] for b in soon}
        assert soon_ids.isdisjoint(expired_ids)
        print("OK: expired and expiring-soon lists are disjoint")

        # --- Mark expired batch as loss ---
        models.dispose_batch(conn, expired_batch, reason="expired")
        batch_row = conn.execute("SELECT * FROM stock_batches WHERE id=?", (expired_batch,)).fetchone()
        assert batch_row["quantity"] == 0
        assert batch_row["status"] == "disposed"
        ret = conn.execute("SELECT * FROM returns WHERE batch_id=?", (expired_batch,)).fetchone()
        assert ret["quantity"] == 10
        assert ret["reason"] == "expired"
        print("OK: dispose_batch(reason='expired') zeroes qty, marks disposed, logs a returns row")

        # After disposal, it must drop out of the expired list (status no longer active)
        expired_after = models.list_expired_batches(conn, today_str)
        assert len(expired_after) == 0
        print("OK: disposed batch no longer appears in list_expired_batches")

        # --- Return-to-supplier path on the soon-expiring batch ---
        models.dispose_batch(conn, soon_batch, reason="supplier_return")
        batch_row2 = conn.execute("SELECT * FROM stock_batches WHERE id=?", (soon_batch,)).fetchone()
        assert batch_row2["quantity"] == 0 and batch_row2["status"] == "disposed"
        ret2 = conn.execute("SELECT * FROM returns WHERE batch_id=?", (soon_batch,)).fetchone()
        assert ret2["reason"] == "supplier_return" and ret2["quantity"] == 6
        print("OK: dispose_batch(reason='supplier_return') works correctly")

        # invalid reason must be rejected
        try:
            models.dispose_batch(conn, expired_batch, reason="customer_return")
            raise AssertionError("expected ValueError for invalid reason")
        except ValueError:
            print("OK: dispose_batch rejects reasons other than 'expired'/'supplier_return'")

        conn.close()

    print("\nAll expiry tests passed.")


if __name__ == "__main__":
    run()

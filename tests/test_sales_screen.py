"""Headless GUI test for ui/sales_screen.py.

Run with: QT_QPA_PLATFORM=offscreen python tests/test_sales_screen.py
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
import models
from ui.pages.sales_page import SalesScreen


def run():
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_pos.db"
        conn = database.init_db(db_path)
        admin = auth.login(conn, "admin", "admin123")

        milk_id = models.create_product(conn, "شیر", "1234567890123", "زیوی", 1000, min_stock=5)
        models.add_stock_batch(conn, milk_id, purchase_price=700, quantity=10, expiry_date="2026-01-01")
        models.add_stock_batch(conn, milk_id, purchase_price=850, quantity=20, expiry_date="2026-06-01")

        cheese_id = models.create_product(conn, "پەنیر", "9998887776665", "زیوی", 2500, min_stock=5)
        models.add_stock_batch(conn, cheese_id, purchase_price=1800, quantity=5, expiry_date=None)

        screen = SalesScreen(conn, admin)

        # --- Scan milk barcode -> new cart line qty 1 ---
        screen.barcode_input.setText("1234567890123")
        screen.on_barcode_scanned()
        assert len(screen.cart) == 1
        assert screen.cart[0]["quantity"] == 1
        print("OK: scanning new barcode adds a cart line with qty 1")

        # --- Scan again -> qty increments, not a duplicate row ---
        screen.barcode_input.setText("1234567890123")
        screen.on_barcode_scanned()
        assert len(screen.cart) == 1
        assert screen.cart[0]["quantity"] == 2
        print("OK: scanning same barcode again increments quantity (no duplicate row)")

        # --- Unknown barcode -> error shown, cart unchanged ---
        screen.barcode_input.setText("0000000000000")
        screen.on_barcode_scanned()
        assert len(screen.cart) == 1
        assert screen.error_label.text() != ""
        print("OK: unknown barcode shows error, cart unaffected")

        # --- Manual search-and-add for cheese ---
        cheese_row = models.find_product_by_barcode(conn, "9998887776665")
        screen.add_to_cart(cheese_row)
        assert len(screen.cart) == 2
        print("OK: manual add-to-cart (search path) works")

        # --- +/- quantity buttons ---
        screen.change_quantity(0, 5)  # milk: 2 -> 7
        assert screen.cart[0]["quantity"] == 7
        screen.change_quantity(0, -100)  # clamps at 1 minimum
        assert screen.cart[0]["quantity"] == 1
        print("OK: quantity +/- buttons adjust and clamp at minimum 1")

        # reset milk qty to 15 to force a FIFO split across its two batches (10 + 20)
        screen.cart[0]["quantity"] = 15
        screen.refresh_cart_table()
        assert screen.subtotal() == 15 * 1000 + 1 * 2500
        print("OK: subtotal computed correctly across multiple lines:", screen.subtotal())

        # --- Discount validation: cannot exceed subtotal ---
        screen.discount_input.setValue(999_999)
        result = screen.complete_sale()
        assert result is None
        assert "داشکاندن" in screen.error_label.text()
        print("OK: discount greater than subtotal is rejected")

        # --- Valid discount, complete sale ---
        screen.discount_input.setValue(1000)
        receipt = screen.complete_sale()
        assert receipt is not None
        assert receipt["subtotal"] == 17500
        assert receipt["discount"] == 1000
        assert receipt["final"] == 16500
        print("OK: sale completed with correct receipt totals (17,500 - 1,000 = 16,500)")

        # Verify FIFO split actually happened in the DB
        batches = conn.execute(
            "SELECT * FROM stock_batches WHERE product_id=? ORDER BY expiry_date", (milk_id,)
        ).fetchall()
        assert batches[0]["quantity"] == 0, "nearest-expiry batch should be fully depleted (10 taken)"
        assert batches[1]["quantity"] == 15, "second batch should have 20-5=15 left"
        print("OK: FIFO deduction confirmed in DB after sale (nearest-expiry batch depleted first)")

        sale_items = conn.execute(
            "SELECT * FROM sale_items WHERE sale_id=?", (receipt["sale_id"],)
        ).fetchall()
        assert len(sale_items) == 3, f"expected 3 rows (2 milk batches + 1 cheese batch), got {len(sale_items)}"
        print("OK: sale_items has one row per (product, batch) combination — 3 rows total")

        # --- Cart is cleared after receipt shown / clear_cart called manually ---
        screen.clear_cart()
        assert screen.cart == []
        assert screen.discount_input.value() == 0
        print("OK: clear_cart resets cart and discount")

        # --- Insufficient stock scenario ---
        screen.add_to_cart(cheese_row)
        screen.cart[0]["quantity"] = 999  # far more than the 4 remaining cheese units
        result2 = screen.complete_sale()
        assert result2 is None
        assert "کۆگا" in screen.error_label.text()
        print("OK: over-selling beyond available stock is rejected with a Kurdish error message")

        conn.close()

    print("\nAll sales screen tests passed.")


if __name__ == "__main__":
    run()

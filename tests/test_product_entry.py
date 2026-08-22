"""Headless GUI test for ui/product_entry.py.

Run with: QT_QPA_PLATFORM=offscreen python tests/test_product_entry.py
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
from ui.pages.products_page import ProductEntryScreen


def run():
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_pos.db"
        conn = database.init_db(db_path)
        admin = auth.login(conn, "admin", "admin123")

        screen = ProductEntryScreen(conn, admin)

        # --- Scenario 1: brand new product via generated barcode ---
        screen.generate_barcode()
        barcode = screen.barcode_input.text()
        assert barcode.startswith("9")
        assert screen.existing_product is None
        screen.name_input.setText("شیر")
        screen.category_input.setText("زیوی")
        screen.sale_price_input.setValue(1000)
        screen.purchase_price_input.setValue(700)
        screen.quantity_input.setValue(50)
        screen.no_expiry_checkbox.setChecked(False)
        screen.expiry_input.setDate(screen.expiry_input.date())
        assert screen.save() is True

        product = models.find_product_by_barcode(conn, barcode)
        assert product is not None and product["name"] == "شیر"
        assert models.get_total_stock(conn, product["id"]) == 50
        batches = conn.execute(
            "SELECT * FROM stock_batches WHERE product_id=?", (product["id"],)
        ).fetchall()
        assert len(batches) == 1
        print("OK: new product saved via form with first batch (qty=50)")

        # --- Scenario 2: scan same barcode again -> restock mode ---
        screen.barcode_input.setText(barcode)
        screen.on_barcode_entered()
        assert screen.existing_product is not None
        assert screen.name_input.isEnabled() is False  # identity locked in restock mode
        assert screen.mode_label.text() != ""
        print("OK: rescanning existing barcode switches to restock mode, locks identity fields")

        # Restock at a DIFFERENT purchase price and expiry
        screen.purchase_price_input.setValue(850)
        screen.quantity_input.setValue(30)
        screen.no_expiry_checkbox.setChecked(False)
        from PySide6.QtCore import QDate
        screen.expiry_input.setDate(QDate(2026, 6, 1))
        assert screen.save() is True

        batches2 = conn.execute(
            "SELECT * FROM stock_batches WHERE product_id=? ORDER BY id", (product["id"],)
        ).fetchall()
        assert len(batches2) == 2, f"expected 2 batches after restock, got {len(batches2)}"
        assert batches2[0]["purchase_price"] == 700
        assert batches2[1]["purchase_price"] == 850
        assert batches2[1]["quantity"] == 30
        assert models.get_total_stock(conn, product["id"]) == 80
        print("OK: restocking at a different price created a SECOND batch row (not an update)")
        print("OK: total stock after restock = 80 (50 + 30)")

        # --- Scenario 3: unknown barcode entered manually -> new empty form ---
        screen.reset_form()
        screen.barcode_input.setText("1112223334445")
        screen.on_barcode_entered()
        assert screen.existing_product is None
        assert screen.name_input.text() == ""
        print("OK: unknown barcode shows empty new-product form")

        # --- Scenario 4: low stock detection reflected in table refresh ---
        screen.refresh_table()
        assert screen.table.rowCount() == 1  # only "شیر" was actually saved
        print("OK: product table refreshed correctly after saves")

        conn.close()

    print("\nAll product entry screen tests passed.")


if __name__ == "__main__":
    run()

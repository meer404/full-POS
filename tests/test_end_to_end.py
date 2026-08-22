"""Full end-to-end headless test: product entry -> sale -> report -> expiry -> backup.

Run with: QT_QPA_PLATFORM=offscreen python tests/test_end_to_end.py
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

import auth
import backup
import database
import models
from ui.pages.products_page import ProductEntryScreen
from ui.pages.sales_page import SalesScreen
from ui.pages.reports_page import ReportsScreen
from ui.pages.expiry_page import ExpiryScreen
from ui.pages.users_page import UsersScreen
from main import MainWindow


def run():
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "pos.db"
        conn = database.init_db(db_path)
        admin = auth.login(conn, "admin", "admin123")
        assert admin is not None
        print("OK: admin logged in")

        # ---------- 1. Product entry: two products, one restocked at a new price ----------
        entry = ProductEntryScreen(conn, admin)
        entry.generate_barcode()
        milk_barcode = entry.barcode_input.text()
        entry.name_input.setText("شیر")
        entry.category_input.setText("زیوی")
        entry.sale_price_input.setValue(1000)
        entry.purchase_price_input.setValue(700)
        entry.quantity_input.setValue(20)
        entry.expiry_input.setDate(QDate.currentDate().addDays(2))  # expiring soon
        assert entry.save() is True

        entry.barcode_input.setText(milk_barcode)
        entry.on_barcode_entered()
        entry.purchase_price_input.setValue(850)
        entry.quantity_input.setValue(30)
        entry.expiry_input.setDate(QDate.currentDate().addDays(200))
        assert entry.save() is True

        entry.reset_form()
        entry.generate_barcode()
        bread_barcode = entry.barcode_input.text()
        entry.name_input.setText("نان")
        entry.category_input.setText("نانەوایی")
        entry.sale_price_input.setValue(500)
        entry.purchase_price_input.setValue(300)
        entry.quantity_input.setValue(3)  # deliberately below min_stock to trigger low-stock alert
        entry.min_stock_input.setValue(10)
        entry.no_expiry_checkbox.setChecked(True)
        assert entry.save() is True

        entry.refresh_table()
        assert entry.table.rowCount() == 2
        low_stock = models.list_low_stock_products(conn)
        assert any(p["name"] == "نان" for p in low_stock)
        print("OK: two products entered, milk has 2 batches (50 total), bread is low-stock")

        # ---------- 2. Sales: FIFO across milk's two batches + bread ----------
        sales = SalesScreen(conn, admin)
        sales.barcode_input.setText(milk_barcode)
        sales.on_barcode_scanned()
        sales.cart[0]["quantity"] = 25  # forces split: 20 from batch1 + 5 from batch2
        sales.barcode_input.setText(bread_barcode)
        sales.on_barcode_scanned()
        sales.refresh_cart_table()
        sales.discount_input.setValue(1000)

        receipt = sales.complete_sale()
        assert receipt is not None
        expected_subtotal = 25 * 1000 + 1 * 500
        assert receipt["subtotal"] == expected_subtotal
        assert receipt["final"] == expected_subtotal - 1000
        print(f"OK: sale completed, receipt #{receipt['sale_id']}, final {receipt['final']:,} IQD")

        milk_id = models.find_product_by_barcode(conn, milk_barcode)["id"]
        assert models.get_total_stock(conn, milk_id) == 25  # 50 - 25 sold
        print("OK: post-sale stock correct (50 - 25 = 25 remaining)")

        # sales.created_at defaults to UTC (SQLite CURRENT_TIMESTAMP) but ReportsScreen
        # filters by local date (QDate::currentDate()); pin it to local "now" so this test
        # isn't flaky within a few hours of local midnight (test-only adjustment).
        conn.execute(
            "UPDATE sales SET created_at = datetime('now', 'localtime') WHERE id = ?",
            (receipt["sale_id"],),
        )
        conn.commit()

        # ---------- 3. Reports: today's numbers reflect the sale ----------
        reports = ReportsScreen(conn)
        assert reports.receipt_stat.value_label.text() == "1"
        assert reports.qty_stat.value_label.text() == "26"
        expected_profit = (1000 - 700) * 20 + (1000 - 850) * 5 + (500 - 300) * 1
        assert str(reports.profit_stat.value_label.text()).replace(" د.ع", "").replace(",", "") == str(expected_profit)
        print("OK: reports screen reflects the sale correctly (1 receipt, 26 items, profit matches FIFO cost)")

        # ---------- 4. Expiry management: milk's near-expiry batch shows a warning ----------
        expiry = ExpiryScreen(conn)
        assert expiry.warning_table.rowCount() >= 1
        warned_names = {expiry.warning_table.item(r, 0).text() for r in range(expiry.warning_table.rowCount())}
        assert "شیر" in warned_names
        print("OK: expiry screen flags milk's soon-expiring batch as a warning")

        # ---------- 5. User management: add a cashier, verify role-based tabs ----------
        users = UsersScreen(conn, admin)
        assert users.add_user("cashier1", "pass123", "cashier") is True
        cashier = auth.login(conn, "cashier1", "pass123")
        assert cashier is not None
        print("OK: cashier account created")

        admin_window = MainWindow(conn, admin)
        cashier_window = MainWindow(conn, cashier)
        assert admin_window.stack.count() == 5, "admin should see all 5 pages"
        assert cashier_window.stack.count() == 2, "cashier should see only Sales + Product Entry"
        admin_tab_labels = set(admin_window._page_titles)
        cashier_tab_labels = set(cashier_window._page_titles)
        assert cashier_tab_labels == {"فرۆشتن", "زیادکردنی بەرهەم"}
        assert admin_tab_labels.issuperset(cashier_tab_labels)
        print("OK: role-based tab visibility correct (cashier sees 2 tabs, admin sees 5)")

        conn.commit()
        conn.close()

        # ---------- 6. Backup on close ----------
        backup_path = backup.create_backup(db_path, tmp_path / "backups")
        assert backup_path is not None and backup_path.exists()
        assert backup_path.stat().st_size > 0
        print("OK: backup file created successfully after closing:", backup_path.name)

    print("\nFull end-to-end scenario passed: product entry -> sale -> report -> expiry -> users -> backup.")


if __name__ == "__main__":
    run()

"""Ad-hoc screenshot generator for any main-window screen (design review only).

Usage: python shot_screen.py <screen_name> <output_path.png>
screen_name one of: product_entry, sales, reports, expiry, users
"""
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

import auth
import database
import models
from ui.style import apply_app_style
from screenshot_helpers import save_screenshot

SCREEN = sys.argv[1]
OUT = sys.argv[2]

app = QApplication.instance() or QApplication([])
apply_app_style(app)

tmp = tempfile.mkdtemp()
db_path = Path(tmp) / "test_pos.db"
conn = database.init_db(db_path)
admin = auth.login(conn, "admin", "admin123")

# Seed some representative data so the screenshot isn't empty.
milk_id = models.create_product(conn, "شیر", "1234567890123", "زیوی", 1000, min_stock=10)
models.add_stock_batch(conn, milk_id, purchase_price=700, quantity=10, expiry_date=(date.today() + timedelta(days=3)).isoformat())
models.add_stock_batch(conn, milk_id, purchase_price=850, quantity=20, expiry_date=(date.today() + timedelta(days=200)).isoformat())

cheese_id = models.create_product(conn, "پەنیر", "9998887776665", "زیوی", 2500, min_stock=15)
models.add_stock_batch(conn, cheese_id, purchase_price=1800, quantity=5, expiry_date=None)

bread_id = models.create_product(conn, "نان", "5556667778889", "نانەوایی", 500, min_stock=20)
models.add_stock_batch(conn, bread_id, purchase_price=300, quantity=3, expiry_date=(date.today() - timedelta(days=1)).isoformat())

models.complete_sale(
    conn,
    cart_items=[{"product_id": milk_id, "quantity": 5, "unit_price": 1000}],
    discount=500,
    cashier_id=admin.id,
)

if SCREEN == "product_entry":
    from ui.product_entry import ProductEntryScreen
    screen = ProductEntryScreen(conn, admin)
elif SCREEN == "sales":
    from ui.sales_screen import SalesScreen
    screen = SalesScreen(conn, admin)
    screen.barcode_input.setText("1234567890123")
    screen.on_barcode_scanned()
    screen.add_to_cart(models.find_product_by_barcode(conn, "9998887776665"))
elif SCREEN == "reports":
    from ui.reports_screen import ReportsScreen
    screen = ReportsScreen(conn)
elif SCREEN == "expiry":
    from ui.expiry_screen import ExpiryScreen
    screen = ExpiryScreen(conn)
elif SCREEN == "users":
    from ui.users_screen import UsersScreen
    auth.create_user(conn, "cashier1", "pass123", "cashier")
    screen = UsersScreen(conn, admin)
elif SCREEN == "main_admin":
    from main import MainWindow
    screen = MainWindow(conn, admin)
elif SCREEN == "main_cashier":
    from main import MainWindow
    cashier = auth.login(conn, "cashier1", "pass123") if auth.login(conn, "cashier1", "pass123") else None
    if cashier is None:
        auth.create_user(conn, "cashier1", "pass123", "cashier")
        cashier = auth.login(conn, "cashier1", "pass123")
    screen = MainWindow(conn, cashier)
else:
    raise SystemExit(f"unknown screen: {SCREEN}")

out = save_screenshot(screen, OUT, size=(1200, 760))
print("Saved:", out)
conn.close()

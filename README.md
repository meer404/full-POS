# سیستەمی خەزنە / فرۆشتن (Market POS System)

Offline desktop point-of-sale system for a market cashier, built with Python + PySide6.
The UI is entirely Kurdish (Sorani, right-to-left); currency is Iraqi Dinar (IQD, whole numbers only).
No server, no network — everything runs locally against a SQLite file.

## Requirements

- Python 3.11+
- PySide6

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

On first run this creates `data/pos.db` with the schema and seeds a default admin account:

- **username:** `admin`
- **password:** `admin123`

Change this password immediately from the Users tab after first login.

## Project structure

```
main.py             application entry point (login -> main window)
database.py          schema + init_db()
auth.py               login / user management helpers
models.py             product, stock batch, sale (FIFO), report, expiry helpers
backup.py             automatic DB backup + pruning
ui/
  style.py            shared RTL stylesheet
  login_screen.py
  product_entry.py
  sales_screen.py
  reports_screen.py
  expiry_screen.py
  users_screen.py
data/pos.db           created automatically
backups/              timestamped DB backups (10 most recent kept)
tests/                headless tests (QT_QPA_PLATFORM=offscreen), one per module
```

## Testing

Every module has a headless test that runs without opening a window:

```bash
python tests/test_database.py
python tests/test_auth.py
python tests/test_models.py
python tests/test_sale_fifo.py
python tests/test_reports.py
python tests/test_expiry.py
python tests/test_backup.py

# GUI screens need the offscreen Qt platform:
QT_QPA_PLATFORM=offscreen python tests/test_login_screen.py
QT_QPA_PLATFORM=offscreen python tests/test_product_entry.py
QT_QPA_PLATFORM=offscreen python tests/test_sales_screen.py
QT_QPA_PLATFORM=offscreen python tests/test_reports_screen.py
QT_QPA_PLATFORM=offscreen python tests/test_expiry_screen.py
QT_QPA_PLATFORM=offscreen python tests/test_users_screen.py
QT_QPA_PLATFORM=offscreen python tests/test_end_to_end.py
```

On Windows PowerShell, set the env var first: `$env:QT_QPA_PLATFORM = "offscreen"`.

## Key design notes

- **Batches, not stock counters.** Every restock inserts a new `stock_batches` row rather
  than updating an existing one, so purchase price and expiry date are preserved per batch.
- **FIFO sales.** Checkout deducts from a product's active batches ordered by nearest
  expiry date first (batches without an expiry date are consumed last, oldest-received first).
  A single sale line can span multiple batches; each (product, batch) pair gets its own
  `sale_items` row so cost/profit stays accurate per batch.
- **Local barcodes.** Generated barcodes always start with `9` and are 13 digits long,
  reserved so they never collide with real-world EAN-13 codes.
- **Permissions.** Cashiers see only the Sales and Product Entry tabs; Reports, Expiry
  Management, and User Management are admin-only (enforced by which tabs `main.py` adds
  to the window, based on the logged-in user's role).
- **Receipts.** Phase 1 shows the receipt in an on-screen dialog. The sale-completion logic
  (`SalesScreen.complete_sale`) is separate from the dialog display (`show_receipt_dialog`),
  so wiring up a 58mm/80mm thermal printer later only means replacing that one method.
- **Discount** is a flat IQD amount entered at checkout, not a percentage.
- **Backup.** On window close, `backup.py` copies `data/pos.db` into `backups/` as
  `backup_YYYY-MM-DD_HHMM.db` and prunes anything beyond the 10 most recent files.

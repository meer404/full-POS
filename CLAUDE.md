# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An offline desktop POS/cashier system for a market, built with Python + PySide6. The UI is
entirely Kurdish (Sorani, right-to-left); currency is Iraqi Dinar (IQD), whole numbers only —
never format or store a price as a float. No server, no network, no external SDKs: everything
runs against a local SQLite file (`data/pos.db`), and barcode scanners are treated as a plain
USB keyboard sending digits + Enter into whichever field has focus.

## Commands

```bash
pip install -r requirements.txt   # only dependency is PySide6
python main.py                    # run the app (default login: admin / admin123)
```

There is no build step, linter config, or formatter configured in this repo — none is enforced.

### Tests

Every module has its own headless test script in `tests/`; there is no pytest runner or
test-discovery config — each file is a standalone `if __name__ == "__main__": run()` script,
so run one at a time (or loop over them, as shown below):

```bash
# Pure-logic modules — no Qt platform needed:
python tests/test_database.py
python tests/test_auth.py
python tests/test_models.py
python tests/test_sale_fifo.py
python tests/test_reports.py
python tests/test_expiry.py
python tests/test_backup.py

# GUI screen tests — MUST set QT_QPA_PLATFORM=offscreen or they will try to open a real window:
QT_QPA_PLATFORM=offscreen python tests/test_login_screen.py
QT_QPA_PLATFORM=offscreen python tests/test_product_entry.py
QT_QPA_PLATFORM=offscreen python tests/test_sales_screen.py
QT_QPA_PLATFORM=offscreen python tests/test_reports_screen.py
QT_QPA_PLATFORM=offscreen python tests/test_expiry_screen.py
QT_QPA_PLATFORM=offscreen python tests/test_users_screen.py
QT_QPA_PLATFORM=offscreen python tests/test_end_to_end.py   # full product-entry -> sale -> report -> expiry -> backup scenario
```

On Windows PowerShell: `$env:QT_QPA_PLATFORM = "offscreen"` before running a GUI test.

Every test creates its own SQLite DB in a `tempfile.TemporaryDirectory()` — never against
`data/pos.db` — so tests are safe to run repeatedly without touching real data. When adding a
new module, add a matching `tests/test_<module>.py` in this same standalone style before
moving on, per the project's original build order (see "Development order" below).

## Architecture

### Data model — batches, not stock counters

`products` (identity, name, barcode, sale_price, min_stock) is deliberately separate from
`stock_batches` (purchase_price, quantity, expiry_date, received_at, status). **Every restock
inserts a new `stock_batches` row — it never updates an existing one.** This is the core
invariant of the whole system: it's what lets the same product carry different purchase prices
and expiry dates across multiple deliveries simultaneously. `models.add_stock_batch()` is the
only place a batch is created; nothing should ever `UPDATE stock_batches SET quantity = quantity
+ ...` to "restock" — that would silently merge distinct price/expiry lots.

A product's total stock and nearest expiry are *derived*, not stored — see
`models.get_total_stock()` / `get_nearest_expiry()`, which sum/min over `status='active'`
batches. `models.list_products_with_stock()` recomputes these per product on every call; there's
no cached total to keep in sync.

### FIFO checkout is the load-bearing piece of logic

`models.complete_sale()` is where a cart becomes a `sales` row + `sale_items` rows. For each
cart line it calls `models.get_active_batches_fifo(product_id)`, which orders active batches by
**nearest `expiry_date` first**, with `NULL`-expiry batches sorted last (ordered among
themselves by oldest `received_at`). It then walks that list, deducting from each batch until
the requested quantity is satisfied — a single cart line can and often does split across two or
more batches, and a **separate `sale_items` row is written per (product, batch) pair actually
touched**, each carrying that batch's own cost basis via `batch_id`. This is why profit
(`reports_screen.py` / `models.sales_report()`) is computed by joining `sale_items` to
`stock_batches` on `batch_id` rather than by looking up the product's current purchase price —
the same product sold in one sale can have two different costs.

`complete_sale()` wraps everything in a single transaction: if total active stock across all
batches for any line is less than requested, it raises `InsufficientStockError` and rolls back
before creating any `sales`/`sale_items` rows — nothing is partially committed.

### The save()/on_X_clicked() split, and why it exists

Every screen with a "commit this action" button (product save, sale checkout, mark-as-loss,
add-user, etc.) splits into two methods:

- a **core logic method** (`save()`, `complete_sale()`, `mark_as_loss()`, `add_user()`, ...)
  that touches the DB, sets `self.error_label` on failure, and returns a plain value
  (`bool`/`dict`/`None`) — no dialogs, safe to call directly from a headless test.
- a **UI-facing slot** (`on_save_clicked()`, `on_complete_clicked()`, ...) wired to the button's
  `clicked` signal, which calls the core method and *then* shows a blocking `QMessageBox`.

This split is not optional style — it's required for testability. `QMessageBox.exec()` opens a
real modal event loop; under `QT_QPA_PLATFORM=offscreen` there is no user to click it, so calling
a slot that shows one directly from a test **hangs forever** (this happened during development;
see git history / test file comments). Any new "commit" action must follow the same split:
write the logic method first, prove it with a headless test, then wire a thin dialog-showing
slot on top.

### Screen <-> permission wiring lives in main.py, not in the screens

`ui/*.py` screens do not check `user.role` to hide themselves — `MainWindow.__init__` in
`main.py` decides which tabs to `addTab()` at all, based on `user.is_admin`
(`auth.User.is_admin`). Sales and Product Entry are added unconditionally; Reports, Expiry
Management, and User Management are only added when `user.is_admin` is true. Field-level
permission (e.g. only an admin can change `sale_price` on an existing product) is instead
enforced inside the screen itself — see `ProductEntryScreen.on_barcode_entered()` /
`.save()`, which gate `sale_price_input` edits on `self.user.is_admin`. When adding a new
permission-gated feature, decide which pattern applies: whole-tab visibility → `main.py`;
partial in-screen field gating → inside the screen using `self.user.is_admin`.

### Kurdish/RTL UI conventions

- All user-facing strings (labels, button text, error messages, dialog titles) are Kurdish
  Sorani. Code identifiers, comments, and commit messages stay in English — this split is
  intentional (see README) so the codebase stays readable for future non-Kurdish-speaking
  development while the product itself stays fully localized.
- `ui/style.py` centralizes the RTL layout direction and stylesheet
  (`apply_app_style(app)`, called once in `main.py`) plus semantic Qt properties used for
  styling hooks: `QLabel[role="title"|"total"|"error"|"warning"]`,
  `QPushButton[danger="true"|secondary="true"]`. Reuse these properties on new widgets instead
  of hand-rolling inline styles, to keep the look consistent.
- Local (store-generated) barcodes always start with `"9"` and are 13 digits
  (`models.generate_local_barcode`, prefix reserved via `LOCAL_BARCODE_PREFIX`) specifically so
  they can never collide with real-world EAN-13 codes scanned off actual products.

### Backup

`backup.create_backup()` copies `data/pos.db` into `backups/backup_<timestamp>.db` and calls
`prune_old_backups()` to keep only the 10 most recent (by mtime). `MainWindow.closeEvent()` in
`main.py` is the only caller in the running app — it commits/closes the DB connection first,
then backs up, so the copied file is never mid-transaction.

### Development order

The project was built and tested in dependency order — `database.py` → `auth.py`/login →
product entry → sales (FIFO) → reports → expiry → users → backup → full end-to-end test — with
a passing headless test written for each module before moving to the next. Follow the same
order for new features that span multiple layers: schema/model change first (with a
`tests/test_*.py` proving it), then the screen that uses it.

# Prompt for Claude Code — Build a Complete Market POS/Cashier System (Start to Finish)

> Give this file as a single initial prompt to Claude Code (in the `claude` terminal command, inside an empty folder). You can paste it all at once.

---

## 🎯 Goal

Build a **Desktop application** in **Python** for a market's cashier/POS system. The application must run **fully offline** on a **single computer, with no server and no network**. The **UI language must be entirely Kurdish (Sorani, Right-to-Left)**, and the currency is the **Iraqi Dinar (IQD)** — whole numbers only, no decimals.

## 🧰 Technical Requirements

- **Language:** Python 3.11+
- **GUI Framework:** PySide6 (not PyQt, not Tkinter)
- **Database:** SQLite (a local file at `data/pos.db`), no external server
- **Barcode Scanner:** No special SDK or code is needed — scanners behave like a USB keyboard and send digits + Enter into whichever input field is focused
- **Structure:** The project must be cleanly organized (database, models, ui/, reports/, main.py)
- **Testing:** After building each part, test it with a headless Python script (no GUI needed) before moving to the next part — e.g. using `QT_QPA_PLATFORM=offscreen`

---

## 🗄️ Database Design (follow this schema precisely)

### `products` table
```
id            INTEGER PRIMARY KEY AUTOINCREMENT
name          TEXT NOT NULL
barcode       TEXT UNIQUE NOT NULL
category      TEXT
sale_price    INTEGER NOT NULL
unit          TEXT DEFAULT 'دانە'
min_stock     INTEGER DEFAULT 5
created_at    TEXT DEFAULT CURRENT_TIMESTAMP
```
> Note: purchase price, quantity, and expiry date are NOT stored here — those live in `stock_batches`.

### `stock_batches` table (critical — this is the foundation of FIFO and expiry tracking)
```
id                 INTEGER PRIMARY KEY AUTOINCREMENT
product_id         INTEGER NOT NULL REFERENCES products(id)
purchase_price     INTEGER NOT NULL
quantity           INTEGER NOT NULL          -- remaining quantity
initial_quantity   INTEGER NOT NULL          -- originally received quantity
expiry_date        TEXT (nullable)           -- NULL for products with no expiry
received_at        TEXT DEFAULT CURRENT_TIMESTAMP
status             TEXT DEFAULT 'active'     -- active / expired / disposed
```
Every time the same product (same barcode) is restocked, a **new row** must be created in this table (a new batch) — never update the old row — so that if the purchase price or expiry date differs, both are preserved separately.

### `sales` table
```
id             INTEGER PRIMARY KEY AUTOINCREMENT
total_amount   INTEGER NOT NULL
discount       INTEGER DEFAULT 0
final_amount   INTEGER NOT NULL
cashier_id     INTEGER REFERENCES users(id)
created_at     TEXT DEFAULT CURRENT_TIMESTAMP
```

### `sale_items` table
```
id            INTEGER PRIMARY KEY AUTOINCREMENT
sale_id       INTEGER NOT NULL REFERENCES sales(id)
product_id    INTEGER NOT NULL REFERENCES products(id)
batch_id      INTEGER NOT NULL REFERENCES stock_batches(id)
quantity      INTEGER NOT NULL
unit_price    INTEGER NOT NULL
total_price   INTEGER NOT NULL
```

### `returns` table
```
id            INTEGER PRIMARY KEY AUTOINCREMENT
batch_id      INTEGER NOT NULL REFERENCES stock_batches(id)
quantity      INTEGER NOT NULL
reason        TEXT NOT NULL   -- 'expired' / 'customer_return' / 'supplier_return'
created_at    TEXT DEFAULT CURRENT_TIMESTAMP
```

### `users` table
```
id              INTEGER PRIMARY KEY AUTOINCREMENT
username        TEXT UNIQUE NOT NULL
password_hash   TEXT NOT NULL     -- sha256, never plain text
role            TEXT NOT NULL     -- 'admin' / 'cashier'
```
On first database creation, seed a default admin user: `admin` / `admin123`.

---

## 🧩 Required Modules (build in this order)

### 1. Login System — build this first
- A login screen before the main app window opens
- Verify username/password against the `users` table (sha256 hash)
- After login, the user's role (admin/cashier) determines which tabs are shown

### 2. Product Entry Screen
- A barcode field that stays focused to receive scanner input
- When a barcode is scanned/typed and Enter is pressed:
  - If it exists in `products` → pre-fill the form with the existing info and switch to "add a new batch" mode (only ask for purchase price / quantity / expiry date)
  - If it doesn't exist → show an empty new-product form
- A "Generate local barcode" button that creates a unique barcode, always starting with a reserved prefix (e.g. "9" + 12 digits) so it never collides with real-world barcodes (e.g. EAN-13)
- Fields: name, category, unit, minimum stock (for low-stock alerts), purchase price, sale price, quantity, expiry date (or a "no expiry" checkbox)
- On save: insert into `products` (if new) and always create a new row in `stock_batches`
- A table below listing all products, barcode, sale price, total stock quantity (sum of all active batches), and nearest expiry date

### 3. Sales Screen — the most important module
- A barcode field for scanning
- When a barcode is scanned:
  - Look it up in `products`
  - If it's already in the current sale list → just increase its quantity
  - If it's new → add it to the current sale list with quantity 1
- Must also support manual sales (without barcode) by searching by name or selecting from a product list
- +/- buttons to change quantity, and a delete button to remove a line item from the current sale
- A discount field before checkout
- Display a detail table like this example:

| Item | Price | Qty | Line Total |
|---|---|---|---|
| Milk | 1,000 IQD | 2 | 2,000 IQD |
| Cheese | 2,500 IQD | 1 | 2,500 IQD |

- Show the grand total prominently at the bottom, in a large font
- "Complete Sale" button:
  - **FIFO logic:** for each product, deduct the requested quantity from that product's active batches, ordered by **nearest expiry date first** (if no expiry date, oldest `received_at` first). If one batch doesn't have enough quantity, split the deduction across it and the next batch (careful split logic must be written)
  - Create a row in `sales` (auto-numbered as the receipt number, with timestamp, subtotal, discount, final total)
  - Create rows in `sale_items` — one per (product, batch) combination that was deducted from (since one product could be sold from two different batches in a single sale)
  - Show a success message with the receipt number
  - Clear the current sale list, ready for the next sale

### 4. Reports Screen
- Three filters: daily / weekly / monthly (with a date/range picker)
- For each period, show:
  - Total number of receipts
  - Total quantity of items sold
  - Total revenue (sum of `final_amount`)
  - Total profit = for each `sale_item`: (`unit_price` − that batch's `purchase_price`) × `quantity`, summed across all items
  - Top 5 best-selling products (by quantity)

### 5. Expiry Management Screen
- A list of all active `stock_batches` where `expiry_date <= today`
- Two buttons for each:
  - **"Mark as loss":** zero out that batch's quantity, create a row in `returns` with `reason='expired'` and the lost quantity, and set the batch's `status` to `'disposed'`
  - **"Return to supplier":** same action but with `reason='supplier_return'`
- A separate section for **warnings**: batches with 7 days or less left before expiry (but not yet expired), shown highlighted in a warning color (yellow/orange)

### 6. User Management Screen (admin only)
- Add/remove users (Admin/Cashier)
- Change password

---

## 🔐 Permissions

| Action | Admin | Cashier |
|---|:---:|:---:|
| Add new product | ✅ | ✅ |
| Change sale price | ✅ | ❌ |
| Make a sale | ✅ | ✅ |
| View reports | ✅ | ❌ |
| Manage expiry | ✅ | ❌ |
| Manage users | ✅ | ❌ |

Tabs must be shown/hidden based on the logged-in user's role (a Cashier should only see the Sales tab and the Product Entry tab).

---

## ➕ Additional Requirements

1. **Automatic backup:** when the app closes, copy the `pos.db` file into a `backups/` folder named with the date/time (e.g. `backup_2026-08-21_2000.db`). Keep only the 10 most recent backups and delete older ones.
2. **Low stock alert:** in the Product Entry screen or a simple dashboard, show products whose total stock is below their `min_stock`.
3. **Receipt printing:** for the first phase, just showing the receipt on screen (a dialog) is enough — no special printer is required, but write the code so it's easy to later add a 58mm/80mm thermal printer.
4. **Discount:** implement in the Sales screen as a simple flat-amount discount field (a number, not a percentage).

---

## ✅ Development Order (step by step — Claude Code should follow this order)

1. Set up the project + `database.py` (schema + init_db) + headless test
2. Login system
3. Product Entry screen (test scenarios: new product, restocking the same product at a different price → two batches)
4. Sales screen (test the FIFO logic with a detailed multi-batch scenario)
5. Reports screen
6. Expiry management screen
7. User management screen
8. Automatic backup
9. Full end-to-end test — a complete scenario from product entry to sale to report

**After finishing each step, Claude Code should briefly report what it tested and what the result was, before moving to the next step.**

---

## 📁 Suggested Project Structure

```
pos_system/
├── main.py
├── database.py
├── auth.py
├── requirements.txt
├── README.md
├── data/
│   └── pos.db          (created automatically)
├── backups/
├── ui/
│   ├── login_screen.py
│   ├── product_entry.py
│   ├── sales_screen.py
│   ├── reports_screen.py
│   ├── expiry_screen.py
│   └── users_screen.py
└── tests/
    └── (headless tests for each module)
```

---

## ⚠️ Final Note

If anything is unclear during development, or several approaches could reasonably fit, **ask before deciding** — especially about: how receipt printing should work, whether the discount should be a percentage or a flat amount, and whether the code itself (variable/function names) should be in English or Kurdish (suggestion: keep the code in English, only the UI in Kurdish, so the codebase stays easy to read for future development).

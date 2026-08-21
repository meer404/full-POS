"""SQLite database layer for the POS system.

All monetary values are stored as whole-number Iraqi Dinar (IQD) integers.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "pos.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('admin', 'cashier'))
);

CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    barcode       TEXT UNIQUE NOT NULL,
    category      TEXT,
    sale_price    INTEGER NOT NULL,
    unit          TEXT DEFAULT 'دانە',
    min_stock     INTEGER DEFAULT 5,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stock_batches (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id         INTEGER NOT NULL REFERENCES products(id),
    purchase_price     INTEGER NOT NULL,
    quantity           INTEGER NOT NULL,
    initial_quantity   INTEGER NOT NULL,
    expiry_date        TEXT,
    received_at        TEXT DEFAULT CURRENT_TIMESTAMP,
    status             TEXT DEFAULT 'active' CHECK(status IN ('active', 'expired', 'disposed'))
);

CREATE TABLE IF NOT EXISTS sales (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    total_amount   INTEGER NOT NULL,
    discount       INTEGER DEFAULT 0,
    final_amount   INTEGER NOT NULL,
    cashier_id     INTEGER REFERENCES users(id),
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sale_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id       INTEGER NOT NULL REFERENCES sales(id),
    product_id    INTEGER NOT NULL REFERENCES products(id),
    batch_id      INTEGER NOT NULL REFERENCES stock_batches(id),
    quantity      INTEGER NOT NULL,
    unit_price    INTEGER NOT NULL,
    total_price   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS returns (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id      INTEGER NOT NULL REFERENCES stock_batches(id),
    quantity      INTEGER NOT NULL,
    reason        TEXT NOT NULL CHECK(reason IN ('expired', 'customer_return', 'supplier_return')),
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_batches_product ON stock_batches(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_batches_expiry ON stock_batches(expiry_date);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_batch ON sale_items(batch_id);
"""

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Create schema if missing and seed the default admin user. Returns an open connection."""
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.commit()

    cur = conn.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (DEFAULT_ADMIN_USERNAME, hash_password(DEFAULT_ADMIN_PASSWORD), "admin"),
        )
        conn.commit()

    return conn


if __name__ == "__main__":
    connection = init_db()
    print(f"Database initialized at {DB_PATH}")
    rows = connection.execute("SELECT username, role FROM users").fetchall()
    for row in rows:
        print(dict(row))
    connection.close()

"""Data-access helpers shared across UI screens (products, stock batches, sales, etc.)."""
from __future__ import annotations

import random
import sqlite3

LOCAL_BARCODE_PREFIX = "9"
LOCAL_BARCODE_LENGTH = 13  # prefix + 12 digits, matching EAN-13 length


def generate_local_barcode(conn: sqlite3.Connection) -> str:
    """Generate a unique local barcode starting with the reserved prefix '9'."""
    while True:
        digits = "".join(str(random.randint(0, 9)) for _ in range(LOCAL_BARCODE_LENGTH - 1))
        candidate = LOCAL_BARCODE_PREFIX + digits
        exists = conn.execute(
            "SELECT 1 FROM products WHERE barcode = ?", (candidate,)
        ).fetchone()
        if not exists:
            return candidate


def find_product_by_barcode(conn: sqlite3.Connection, barcode: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM products WHERE barcode = ?", (barcode,)
    ).fetchone()


def search_products_by_name(conn: sqlite3.Connection, query: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM products WHERE name LIKE ? ORDER BY name",
        (f"%{query}%",),
    ).fetchall()


def create_product(
    conn: sqlite3.Connection,
    name: str,
    barcode: str,
    category: str,
    sale_price: int,
    unit: str = "دانە",
    min_stock: int = 5,
) -> int:
    cur = conn.execute(
        "INSERT INTO products (name, barcode, category, sale_price, unit, min_stock) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, barcode, category, sale_price, unit, min_stock),
    )
    conn.commit()
    return cur.lastrowid


def update_product_sale_price(conn: sqlite3.Connection, product_id: int, sale_price: int) -> None:
    conn.execute("UPDATE products SET sale_price = ? WHERE id = ?", (sale_price, product_id))
    conn.commit()


def add_stock_batch(
    conn: sqlite3.Connection,
    product_id: int,
    purchase_price: int,
    quantity: int,
    expiry_date: str | None,
) -> int:
    """Always inserts a NEW batch row — restocking never updates an existing batch."""
    cur = conn.execute(
        "INSERT INTO stock_batches (product_id, purchase_price, quantity, initial_quantity, expiry_date) "
        "VALUES (?, ?, ?, ?, ?)",
        (product_id, purchase_price, quantity, quantity, expiry_date),
    )
    conn.commit()
    return cur.lastrowid


def get_total_stock(conn: sqlite3.Connection, product_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS total FROM stock_batches "
        "WHERE product_id = ? AND status = 'active'",
        (product_id,),
    ).fetchone()
    return row["total"]


def get_nearest_expiry(conn: sqlite3.Connection, product_id: int) -> str | None:
    row = conn.execute(
        "SELECT MIN(expiry_date) AS nearest FROM stock_batches "
        "WHERE product_id = ? AND status = 'active' AND expiry_date IS NOT NULL AND quantity > 0",
        (product_id,),
    ).fetchone()
    return row["nearest"]


def list_products_with_stock(conn: sqlite3.Connection) -> list[dict]:
    products = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    result = []
    for p in products:
        result.append({
            "id": p["id"],
            "name": p["name"],
            "barcode": p["barcode"],
            "category": p["category"],
            "sale_price": p["sale_price"],
            "unit": p["unit"],
            "min_stock": p["min_stock"],
            "total_stock": get_total_stock(conn, p["id"]),
            "nearest_expiry": get_nearest_expiry(conn, p["id"]),
        })
    return result


def list_low_stock_products(conn: sqlite3.Connection) -> list[dict]:
    return [p for p in list_products_with_stock(conn) if p["total_stock"] < p["min_stock"]]


class InsufficientStockError(Exception):
    def __init__(self, product_id: int, requested: int, available: int):
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for product {product_id}: requested {requested}, available {available}"
        )


def complete_sale(
    conn: sqlite3.Connection,
    cart_items: list[dict],
    discount: int,
    cashier_id: int,
) -> int:
    """Complete a sale using FIFO batch deduction (nearest expiry first).

    cart_items: list of {"product_id": int, "quantity": int, "unit_price": int}
    Returns the new sale's id. Raises InsufficientStockError if any product
    lacks enough total active stock; in that case nothing is committed.
    """
    total_amount = sum(item["quantity"] * item["unit_price"] for item in cart_items)
    final_amount = max(total_amount - discount, 0)

    try:
        cur = conn.execute(
            "INSERT INTO sales (total_amount, discount, final_amount, cashier_id) VALUES (?, ?, ?, ?)",
            (total_amount, discount, final_amount, cashier_id),
        )
        sale_id = cur.lastrowid

        for item in cart_items:
            product_id = item["product_id"]
            unit_price = item["unit_price"]
            remaining = item["quantity"]

            batches = get_active_batches_fifo(conn, product_id)
            available = sum(b["quantity"] for b in batches)
            if available < remaining:
                raise InsufficientStockError(product_id, remaining, available)

            for batch in batches:
                if remaining <= 0:
                    break
                take = min(batch["quantity"], remaining)
                new_batch_qty = batch["quantity"] - take
                conn.execute(
                    "UPDATE stock_batches SET quantity = ? WHERE id = ?",
                    (new_batch_qty, batch["id"]),
                )
                conn.execute(
                    "INSERT INTO sale_items (sale_id, product_id, batch_id, quantity, unit_price, total_price) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (sale_id, product_id, batch["id"], take, unit_price, take * unit_price),
                )
                remaining -= take

        conn.commit()
        return sale_id
    except Exception:
        conn.rollback()
        raise


def get_active_batches_fifo(conn: sqlite3.Connection, product_id: int) -> list[sqlite3.Row]:
    """Active batches with quantity > 0, ordered nearest-expiry-first;
    batches with no expiry date come after dated ones and are ordered by oldest received_at first.
    """
    return conn.execute(
        """
        SELECT * FROM stock_batches
        WHERE product_id = ? AND status = 'active' AND quantity > 0
        ORDER BY
            CASE WHEN expiry_date IS NULL THEN 1 ELSE 0 END,
            expiry_date ASC,
            received_at ASC
        """,
        (product_id,),
    ).fetchall()


def list_expired_batches(conn: sqlite3.Connection, today: str) -> list[sqlite3.Row]:
    """Active batches whose expiry_date has already passed (<= today)."""
    return conn.execute(
        """
        SELECT sb.*, p.name AS product_name, p.unit AS unit
        FROM stock_batches sb
        JOIN products p ON p.id = sb.product_id
        WHERE sb.status = 'active' AND sb.expiry_date IS NOT NULL AND sb.expiry_date <= ?
        ORDER BY sb.expiry_date ASC
        """,
        (today,),
    ).fetchall()


def list_expiring_soon_batches(conn: sqlite3.Connection, today: str, warn_date: str) -> list[sqlite3.Row]:
    """Active, not-yet-expired batches with expiry within `warn_date` (today < expiry <= warn_date)."""
    return conn.execute(
        """
        SELECT sb.*, p.name AS product_name, p.unit AS unit
        FROM stock_batches sb
        JOIN products p ON p.id = sb.product_id
        WHERE sb.status = 'active' AND sb.expiry_date IS NOT NULL
              AND sb.expiry_date > ? AND sb.expiry_date <= ?
        ORDER BY sb.expiry_date ASC
        """,
        (today, warn_date),
    ).fetchall()


def dispose_batch(conn: sqlite3.Connection, batch_id: int, reason: str) -> None:
    """Zero out a batch's quantity, log it in `returns`, and mark it disposed.

    reason must be 'expired' or 'supplier_return'.
    """
    if reason not in ("expired", "supplier_return"):
        raise ValueError("reason must be 'expired' or 'supplier_return'")

    batch = conn.execute("SELECT * FROM stock_batches WHERE id = ?", (batch_id,)).fetchone()
    if batch is None:
        raise ValueError(f"No such batch: {batch_id}")

    lost_qty = batch["quantity"]
    conn.execute(
        "INSERT INTO returns (batch_id, quantity, reason) VALUES (?, ?, ?)",
        (batch_id, lost_qty, reason),
    )
    conn.execute(
        "UPDATE stock_batches SET quantity = 0, status = 'disposed' WHERE id = ?",
        (batch_id,),
    )
    conn.commit()


def sales_report(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """Aggregate sales report for [start, end] inclusive, as 'YYYY-MM-DD' date strings.

    Returns receipt_count, total_qty, total_revenue, total_profit, top_products (top 5 by qty).
    """
    date_filter = "DATE(s.created_at) BETWEEN ? AND ?"

    receipt_row = conn.execute(
        f"SELECT COUNT(*) AS c, COALESCE(SUM(s.final_amount), 0) AS revenue "
        f"FROM sales s WHERE {date_filter}",
        (start, end),
    ).fetchone()

    items_row = conn.execute(
        f"""
        SELECT
            COALESCE(SUM(si.quantity), 0) AS total_qty,
            COALESCE(SUM((si.unit_price - sb.purchase_price) * si.quantity), 0) AS total_profit
        FROM sale_items si
        JOIN sales s ON s.id = si.sale_id
        JOIN stock_batches sb ON sb.id = si.batch_id
        WHERE {date_filter}
        """,
        (start, end),
    ).fetchone()

    top_products = conn.execute(
        f"""
        SELECT p.name AS name, SUM(si.quantity) AS qty
        FROM sale_items si
        JOIN sales s ON s.id = si.sale_id
        JOIN products p ON p.id = si.product_id
        WHERE {date_filter}
        GROUP BY si.product_id
        ORDER BY qty DESC
        LIMIT 5
        """,
        (start, end),
    ).fetchall()

    return {
        "receipt_count": receipt_row["c"],
        "total_qty": items_row["total_qty"],
        "total_revenue": receipt_row["revenue"],
        "total_profit": items_row["total_profit"],
        "top_products": [{"name": r["name"], "qty": r["qty"]} for r in top_products],
    }

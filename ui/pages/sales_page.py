"""Sales (cashier) screen: scan/search products, build a cart, complete the sale via FIFO."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import auth
import models
from ui.theme import Colors, apply_card_shadow, icon
from ui.widgets.badge import Badge
from ui.widgets.card import Card
from ui.widgets.data_table import DataTable
from ui.widgets.spin_input import SpinInput
from ui.widgets.toast import show_toast


class _ResultCard(QFrame):
    """One search-result row: name + price + a stock badge, click to add to the cart."""

    picked = Signal(int)

    def __init__(self, product: sqlite3.Row, stock: int, parent=None):
        super().__init__(parent)
        self.setObjectName("resultCard")
        self.setCursor(Qt.PointingHandCursor)
        self._product_id = product["id"]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        name_label = QLabel(product["name"])
        name_label.setProperty("role", "section")
        layout.addWidget(name_label, 1)

        price_label = QLabel(f"{product['sale_price']:,} د.ع")
        price_label.setProperty("role", "caption")
        layout.addWidget(price_label)

        low = stock < (product["min_stock"] or 0)
        badge = Badge("کەمی کۆگا" if low else "بەردەستە", "warning" if low else "success")
        layout.addWidget(badge)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.picked.emit(self._product_id)
        super().mouseReleaseEvent(event)


class SalesScreen(QWidget):
    def __init__(self, conn: sqlite3.Connection, user: auth.User, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.user = user
        # cart: list of dicts {product_id, name, unit_price, quantity}
        self.cart: list[dict] = []
        self.last_receipt: dict | None = None

        self._build_ui()
        self._build_shortcuts()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        # ---- Right (RTL-leading) column: barcode + search + results ----
        left_card = Card("کڕین / گەڕان بۆ بەرهەم")
        left_card.setMinimumWidth(320)

        left_card.body.addWidget(QLabel("بارکۆد:"))
        self.barcode_input = QLineEdit()
        self.barcode_input.setObjectName("barcodeInput")
        self.barcode_input.setLayoutDirection(Qt.LeftToRight)
        self.barcode_input.setPlaceholderText("بارکۆد سکان بکە و Enter دابگرە")
        self.barcode_input.returnPressed.connect(self.on_barcode_scanned)
        left_card.body.addWidget(self.barcode_input)

        left_card.body.addWidget(QLabel("گەڕان بە ناو: (F3)"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("گەڕان بە ناوی بەرهەم...")
        self.search_input.textChanged.connect(self.on_search_changed)
        left_card.body.addWidget(self.search_input)

        self.search_results = QListWidget()
        left_card.body.addWidget(self.search_results, 1)

        root.addWidget(left_card, 35)

        # ---- Left (RTL-trailing) column: cart ----
        right_card = Card("لیستی کڕین")

        self.cart_data_table = DataTable(
            ["بەرهەم", "نرخ", "دانە", "کۆی گشتی", ""],
            empty_icon="fa5s.shopping-basket",
            empty_text="سەبەتەکە بەتاڵە — بارکۆد سکان بکە یان بەرهەمێک بگەڕێ",
        )
        self.cart_table = self.cart_data_table.table
        cart_header = self.cart_table.horizontalHeader()
        cart_header.setSectionResizeMode(0, QHeaderView.Stretch)
        cart_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        cart_header.setSectionResizeMode(2, QHeaderView.Fixed)
        cart_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        cart_header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(2, 110)
        self.cart_table.setColumnWidth(4, 48)
        right_card.body.addWidget(self.cart_data_table, 1)

        bottom_row = QHBoxLayout()

        discount_box = QVBoxLayout()
        discount_box.addWidget(QLabel("داشکاندن (د.ع):"))
        self.discount_input = SpinInput(minimum=0, maximum=999_999_999, suffix=" د.ع")
        self.discount_input.valueChanged.connect(self.update_totals)
        discount_box.addWidget(self.discount_input)
        bottom_row.addLayout(discount_box)

        bottom_row.addStretch()

        total_card = QFrame()
        total_card.setObjectName("totalCard")
        totals_box = QVBoxLayout(total_card)
        totals_box.setContentsMargins(20, 10, 20, 10)
        self.subtotal_label = QLabel("کۆی گشتی: 0 د.ع")
        self.subtotal_label.setProperty("role", "caption")
        self.total_label = QLabel("پارەی کۆتایی: 0 د.ع")
        self.total_label.setProperty("role", "grandtotal")
        totals_box.addWidget(self.subtotal_label)
        totals_box.addWidget(self.total_label)
        bottom_row.addWidget(total_card)

        right_card.body.addLayout(bottom_row)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        right_card.body.addWidget(self.error_label)

        action_row = QHBoxLayout()
        self.complete_btn = QPushButton(" تەواوکردنی فرۆشتن")
        self.complete_btn.setIcon(icon("fa5s.check-circle", "white"))
        self.complete_btn.setIconSize(QSize(18, 18))
        self.complete_btn.setMinimumHeight(56)
        self.complete_btn.setCursor(Qt.PointingHandCursor)
        self.complete_btn.clicked.connect(self.on_complete_clicked)
        self.clear_btn = QPushButton("پاککردنەوە")
        self.clear_btn.setProperty("secondary", True)
        self.clear_btn.setMinimumHeight(56)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_cart)
        action_row.addWidget(self.complete_btn, 2)
        action_row.addWidget(self.clear_btn, 1)
        right_card.body.addLayout(action_row)

        hint_label = QLabel("F2 تەواوکردنی فرۆشتن · F3 گەڕان · Esc پاککردنەوە · Delete سڕینەوەی دانە")
        hint_label.setProperty("role", "caption")
        hint_label.setAlignment(Qt.AlignCenter)
        right_card.body.addWidget(hint_label)

        root.addWidget(right_card, 65)

        self.barcode_input.setFocus()

    def _build_shortcuts(self):
        QShortcut(QKeySequence("F2"), self, activated=self.on_complete_clicked)
        QShortcut(QKeySequence("F3"), self, activated=self.search_input.setFocus)
        QShortcut(QKeySequence("Esc"), self, activated=self.clear_cart)
        QShortcut(QKeySequence("Delete"), self, activated=self._remove_selected_line)

    def _remove_selected_line(self):
        row = self.cart_table.currentRow()
        if row >= 0:
            self.remove_line(row)

    # -------------------------------------------------------------- search
    def on_search_changed(self, text: str):
        self.search_results.clear()
        text = text.strip()
        if not text:
            return
        for product in models.search_products_by_name(self.conn, text):
            stock = models.get_total_stock(self.conn, product["id"])
            item = QListWidgetItem(self.search_results)
            item.setSizeHint(QSize(0, 52))
            card = _ResultCard(product, stock)
            card.picked.connect(self.on_search_result_picked)
            self.search_results.setItemWidget(item, card)

    def on_search_result_picked(self, product_id: int):
        product = self.conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if product:
            self.add_to_cart(product)
        self.search_input.clear()
        self.search_results.clear()

    # ------------------------------------------------------------- barcode
    def on_barcode_scanned(self):
        barcode = self.barcode_input.text().strip()
        self.barcode_input.clear()
        self.error_label.setText("")
        if not barcode:
            return
        product = models.find_product_by_barcode(self.conn, barcode)
        if product is None:
            self.error_label.setText(f"هیچ بەرهەمێک بەم بارکۆدە نەدۆزرایەوە: {barcode}")
            return
        self.add_to_cart(product)

    # ---------------------------------------------------------------- cart
    def add_to_cart(self, product: sqlite3.Row):
        for line in self.cart:
            if line["product_id"] == product["id"]:
                line["quantity"] += 1
                self.refresh_cart_table()
                return
        self.cart.append({
            "product_id": product["id"],
            "name": product["name"],
            "unit_price": product["sale_price"],
            "quantity": 1,
        })
        self.refresh_cart_table()

    def change_quantity(self, index: int, delta: int):
        line = self.cart[index]
        line["quantity"] = max(1, line["quantity"] + delta)
        self.refresh_cart_table()

    def remove_line(self, index: int):
        del self.cart[index]
        self.refresh_cart_table()

    def refresh_cart_table(self):
        self.cart_table.setRowCount(len(self.cart))
        for row, line in enumerate(self.cart):
            self._set_item(row, 0, line["name"])
            self._set_item(row, 1, f"{line['unit_price']:,} د.ع")

            qty_widget = QWidget()
            qty_layout = QHBoxLayout(qty_widget)
            qty_layout.setContentsMargins(4, 4, 4, 4)
            qty_layout.setSpacing(6)
            minus_btn = QPushButton()
            minus_btn.setIcon(icon("fa5s.minus", Colors.TEXT_SECONDARY))
            minus_btn.setFixedSize(28, 28)
            minus_btn.setProperty("secondary", True)
            minus_btn.setCursor(Qt.PointingHandCursor)
            minus_btn.clicked.connect(lambda _, i=row: self.change_quantity(i, -1))
            qty_label = QLabel(str(line["quantity"]))
            qty_label.setAlignment(Qt.AlignCenter)
            qty_label.setMinimumWidth(24)
            plus_btn = QPushButton()
            plus_btn.setIcon(icon("fa5s.plus", Colors.PRIMARY))
            plus_btn.setFixedSize(28, 28)
            plus_btn.setProperty("secondary", True)
            plus_btn.setCursor(Qt.PointingHandCursor)
            plus_btn.clicked.connect(lambda _, i=row: self.change_quantity(i, 1))
            qty_layout.addWidget(minus_btn)
            qty_layout.addWidget(qty_label)
            qty_layout.addWidget(plus_btn)
            self.cart_table.setCellWidget(row, 2, qty_widget)

            line_total = line["unit_price"] * line["quantity"]
            self._set_item(row, 3, f"{line_total:,} د.ع")

            del_btn = QPushButton()
            del_btn.setIcon(icon("fa5s.trash-alt", "white"))
            del_btn.setFixedSize(32, 28)
            del_btn.setProperty("danger", True)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("سڕینەوە")
            del_btn.clicked.connect(lambda _, i=row: self.remove_line(i))
            self.cart_table.setCellWidget(row, 4, del_btn)

        self.update_totals()

    def _set_item(self, row: int, col: int, text: str):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cart_table.setItem(row, col, item)

    def subtotal(self) -> int:
        return sum(line["unit_price"] * line["quantity"] for line in self.cart)

    def update_totals(self):
        subtotal = self.subtotal()
        discount = self.discount_input.value()
        final = max(subtotal - discount, 0)
        self.subtotal_label.setText(f"کۆی گشتی: {subtotal:,} د.ع")
        self.total_label.setText(f"پارەی کۆتایی: {final:,} د.ع")

    def clear_cart(self):
        self.cart = []
        self.discount_input.setValue(0)
        self.error_label.setText("")
        self.refresh_cart_table()
        self.barcode_input.setFocus()

    # ------------------------------------------------------------ checkout
    def on_complete_clicked(self):
        """UI-facing slot: completes the sale then shows the receipt dialog."""
        result = self.complete_sale()
        if result is not None:
            self.show_receipt_dialog(result)
            self.clear_cart()

    def complete_sale(self) -> dict | None:
        """Core checkout logic, no dialogs. Returns a receipt dict on success, else None
        (with self.error_label set). Safe to call headlessly."""
        self.error_label.setText("")
        if not self.cart:
            self.error_label.setText("لیستی کڕین بەتاڵە")
            return None

        discount = self.discount_input.value()
        subtotal = self.subtotal()
        if discount > subtotal:
            self.error_label.setText("داشکاندن ناتوانێت لە کۆی گشتی زیاتر بێت")
            return None

        cart_items = [
            {"product_id": line["product_id"], "quantity": line["quantity"], "unit_price": line["unit_price"]}
            for line in self.cart
        ]
        try:
            sale_id = models.complete_sale(self.conn, cart_items, discount, self.user.id)
        except models.InsufficientStockError as exc:
            self.error_label.setText(
                f"کۆگا نەماوە بۆ ئەم بەرهەمە (داواکراو: {exc.requested}, بەردەست: {exc.available})"
            )
            return None

        final = max(subtotal - discount, 0)
        self.last_receipt = {
            "sale_id": sale_id,
            "items": list(self.cart),
            "subtotal": subtotal,
            "discount": discount,
            "final": final,
        }
        return self.last_receipt

    def show_receipt_dialog(self, receipt: dict):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"پسوڵەی فرۆشتن ژمارە #{receipt['sale_id']}")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.setMinimumWidth(360)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        title = QLabel(f"پسوڵەی فرۆشتن ژمارە #{receipt['sale_id']}")
        title.setProperty("role", "section")
        layout.addWidget(title)

        divider = QFrame()
        divider.setObjectName("cardDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        for line in receipt["items"]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{line['name']} × {line['quantity']}"))
            row.addStretch()
            row.addWidget(QLabel(f"{line['unit_price'] * line['quantity']:,} د.ع"))
            layout.addLayout(row)

        layout.addWidget(divider)
        subtotal_row = QHBoxLayout()
        subtotal_row.addWidget(QLabel("کۆی گشتی:"))
        subtotal_row.addStretch()
        subtotal_row.addWidget(QLabel(f"{receipt['subtotal']:,} د.ع"))
        layout.addLayout(subtotal_row)

        discount_row = QHBoxLayout()
        discount_row.addWidget(QLabel("داشکاندن:"))
        discount_row.addStretch()
        discount_row.addWidget(QLabel(f"{receipt['discount']:,} د.ع"))
        layout.addLayout(discount_row)

        final_row = QHBoxLayout()
        final_label = QLabel("پارەی کۆتایی:")
        final_label.setProperty("role", "section")
        final_value = QLabel(f"{receipt['final']:,} د.ع")
        final_value.setProperty("role", "total")
        final_row.addWidget(final_label)
        final_row.addStretch()
        final_row.addWidget(final_value)
        layout.addLayout(final_row)

        close_btn = QPushButton("داخستن")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()
        show_toast(self.window(), "فرۆشتن سەرکەوتوو تەواو بوو", "success")

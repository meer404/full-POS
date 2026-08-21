"""Sales (cashier) screen: scan/search products, build a cart, complete the sale via FIFO."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import auth
import models
from ui.style import Colors, apply_card_shadow, icon


class SalesScreen(QWidget):
    def __init__(self, conn: sqlite3.Connection, user: auth.User, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.user = user
        # cart: list of dicts {product_id, name, unit_price, quantity}
        self.cart: list[dict] = []
        self.last_receipt: dict | None = None

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        left_box = QGroupBox("کڕین / گەڕان بۆ بەرهەم")
        apply_card_shadow(left_box)
        left = QVBoxLayout(left_box)
        left.setSpacing(12)

        left.addWidget(QLabel("بارکۆد:"))
        self.barcode_input = QLineEdit()
        self.barcode_input.setObjectName("barcodeInput")
        self.barcode_input.setPlaceholderText("بارکۆد سکان بکە و Enter دابگرە")
        self.barcode_input.returnPressed.connect(self.on_barcode_scanned)
        left.addWidget(self.barcode_input)

        left.addSpacing(12)
        left.addWidget(QLabel("گەڕان بە ناو:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("گەڕان بە ناوی بەرهەم...")
        self.search_input.textChanged.connect(self.on_search_changed)
        left.addWidget(self.search_input)

        self.search_results = QListWidget()
        self.search_results.itemDoubleClicked.connect(self.on_search_result_chosen)
        left.addWidget(self.search_results)

        left_box.setMaximumWidth(320)
        root.addWidget(left_box)

        right_box = QGroupBox("لیستی کڕین")
        apply_card_shadow(right_box)
        right = QVBoxLayout(right_box)
        right.setSpacing(16)

        self.cart_table = QTableWidget(0, 5)
        self.cart_table.setHorizontalHeaderLabels(
            ["بەرهەم", "نرخ", "دانە", "کۆی گشتی", ""]
        )
        cart_header = self.cart_table.horizontalHeader()
        cart_header.setSectionResizeMode(0, QHeaderView.Stretch)
        cart_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        cart_header.setSectionResizeMode(2, QHeaderView.Fixed)
        cart_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        cart_header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(2, 110)
        self.cart_table.setColumnWidth(4, 48)
        self.cart_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setMouseTracking(True)
        self.cart_table.verticalHeader().setDefaultSectionSize(44)
        self.cart_table.verticalHeader().setVisible(False)
        right.addWidget(self.cart_table)

        bottom_row = QHBoxLayout()

        discount_box = QVBoxLayout()
        discount_box.addWidget(QLabel("داشکاندن (د.ع):"))
        self.discount_input = QSpinBox()
        self.discount_input.setRange(0, 999_999_999)
        self.discount_input.setMinimumHeight(36)
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

        right.addLayout(bottom_row)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        right.addWidget(self.error_label)

        action_row = QHBoxLayout()
        self.complete_btn = QPushButton(" تەواوکردنی فرۆشتن")
        self.complete_btn.setIcon(icon("fa5s.check-circle", "white"))
        self.complete_btn.setIconSize(QSize(18, 18))
        self.complete_btn.setMinimumHeight(44)
        self.complete_btn.clicked.connect(self.on_complete_clicked)
        self.clear_btn = QPushButton("پاککردنەوە")
        self.clear_btn.setProperty("secondary", True)
        self.clear_btn.setMinimumHeight(44)
        self.clear_btn.clicked.connect(self.clear_cart)
        action_row.addWidget(self.complete_btn, 2)
        action_row.addWidget(self.clear_btn, 1)
        right.addLayout(action_row)

        root.addWidget(right_box)

        self.barcode_input.setFocus()

    # -------------------------------------------------------------- search
    def on_search_changed(self, text: str):
        self.search_results.clear()
        text = text.strip()
        if not text:
            return
        for product in models.search_products_by_name(self.conn, text):
            item = QListWidgetItem(f"{product['name']} — {product['sale_price']:,} د.ع")
            item.setData(Qt.UserRole, product["id"])
            self.search_results.addItem(item)

    def on_search_result_chosen(self, item: QListWidgetItem):
        product_id = item.data(Qt.UserRole)
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
            self.cart_table.setItem(row, 0, QTableWidgetItem(line["name"]))
            self.cart_table.setItem(row, 1, QTableWidgetItem(f"{line['unit_price']:,} د.ع"))

            qty_widget = QWidget()
            qty_layout = QHBoxLayout(qty_widget)
            qty_layout.setContentsMargins(4, 4, 4, 4)
            qty_layout.setSpacing(6)
            minus_btn = QPushButton()
            minus_btn.setIcon(icon("fa5s.minus", Colors.TEXT_SECONDARY))
            minus_btn.setFixedSize(28, 28)
            minus_btn.setProperty("secondary", True)
            minus_btn.clicked.connect(lambda _, i=row: self.change_quantity(i, -1))
            qty_label = QLabel(str(line["quantity"]))
            qty_label.setAlignment(Qt.AlignCenter)
            qty_label.setMinimumWidth(24)
            plus_btn = QPushButton()
            plus_btn.setIcon(icon("fa5s.plus", "white"))
            plus_btn.setFixedSize(28, 28)
            plus_btn.clicked.connect(lambda _, i=row: self.change_quantity(i, 1))
            qty_layout.addWidget(minus_btn)
            qty_layout.addWidget(qty_label)
            qty_layout.addWidget(plus_btn)
            self.cart_table.setCellWidget(row, 2, qty_widget)

            line_total = line["unit_price"] * line["quantity"]
            self.cart_table.setItem(row, 3, QTableWidgetItem(f"{line_total:,} د.ع"))

            del_btn = QPushButton()
            del_btn.setIcon(icon("fa5s.trash-alt", "white"))
            del_btn.setFixedSize(32, 28)
            del_btn.setProperty("danger", True)
            del_btn.clicked.connect(lambda _, i=row: self.remove_line(i))
            self.cart_table.setCellWidget(row, 4, del_btn)

        self.update_totals()

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
        lines = [f"پسوڵەی فرۆشتن ژمارە #{receipt['sale_id']}", "-" * 30]
        for line in receipt["items"]:
            lines.append(
                f"{line['name']} x{line['quantity']} = {line['unit_price'] * line['quantity']:,} د.ع"
            )
        lines.append("-" * 30)
        lines.append(f"کۆی گشتی: {receipt['subtotal']:,} د.ع")
        lines.append(f"داشکاندن: {receipt['discount']:,} د.ع")
        lines.append(f"پارەی کۆتایی: {receipt['final']:,} د.ع")
        QMessageBox.information(self, "پسوڵە", "\n".join(lines))

"""Product entry screen: barcode scan -> new product form OR restock (new batch) form."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import auth
import models
from ui.theme import Colors, icon
from ui.widgets.card import Card
from ui.widgets.data_table import DataTable
from ui.widgets.spin_input import SpinInput
from ui.widgets.toast import show_toast

MAX_PRICE = 999_999_999
MAX_QTY = 1_000_000


def _section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "section")
    return label


class ProductEntryScreen(QWidget):
    def __init__(self, conn: sqlite3.Connection, user: auth.User, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.user = user
        self.existing_product: sqlite3.Row | None = None

        self._build_ui()
        self.refresh_table()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        # ---- Right: form ----
        form_card = Card("زیادکردنی بەرهەم / پڕکردنەوەی کۆگا")
        form_card.setMinimumWidth(380)

        barcode_row = QHBoxLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setObjectName("barcodeInput")
        self.barcode_input.setLayoutDirection(Qt.LeftToRight)
        self.barcode_input.setPlaceholderText("بارکۆد سکان بکە یان بنووسە و Enter دابگرە")
        self.barcode_input.returnPressed.connect(self.on_barcode_entered)
        barcode_row.addWidget(self.barcode_input, 1)
        self.gen_barcode_btn = QPushButton("دروستکردنی بارکۆدی ناوخۆیی")
        self.gen_barcode_btn.setIcon(icon("fa5s.barcode", Colors.TEXT_SECONDARY))
        self.gen_barcode_btn.setProperty("secondary", True)
        self.gen_barcode_btn.setCursor(Qt.PointingHandCursor)
        self.gen_barcode_btn.clicked.connect(self.generate_barcode)
        barcode_row.addWidget(self.gen_barcode_btn)
        form_card.body.addLayout(barcode_row)

        self.mode_label = QLabel("")
        self.mode_label.setProperty("role", "warning")
        self.mode_label.setWordWrap(True)
        form_card.body.addWidget(self.mode_label)

        # ---- Basic info ----
        form_card.body.addWidget(_section_label("زانیاری بنەڕەتی"))
        basic_fields = QFormLayout()
        basic_fields.setVerticalSpacing(12)
        self.name_input = QLineEdit()
        basic_fields.addRow("ناوی بەرهەم:", self.name_input)

        self.category_input = QLineEdit()
        basic_fields.addRow("جۆر:", self.category_input)

        self.unit_input = QComboBox()
        self.unit_input.setEditable(True)
        self.unit_input.addItems(["دانە", "کیلۆگرام", "لیتر", "پاکەت", "کارتۆن"])
        basic_fields.addRow("یەکە:", self.unit_input)
        form_card.body.addLayout(basic_fields)

        # ---- Pricing & stock ----
        form_card.body.addWidget(_section_label("نرخ و کۆگا"))
        pricing_fields = QFormLayout()
        pricing_fields.setVerticalSpacing(12)

        self.min_stock_input = SpinInput(minimum=0, maximum=MAX_QTY, value=5)
        pricing_fields.addRow("کەمترین ڕادەی کۆگا:", self.min_stock_input)

        self.sale_price_input = SpinInput(minimum=0, maximum=MAX_PRICE, suffix=" د.ع")
        pricing_fields.addRow("نرخی فرۆشتن:", self.sale_price_input)

        self.purchase_price_input = SpinInput(minimum=0, maximum=MAX_PRICE, suffix=" د.ع")
        pricing_fields.addRow("نرخی کڕین:", self.purchase_price_input)

        self.margin_label = QLabel("")
        self.margin_label.setProperty("role", "margin")
        pricing_fields.addRow("", self.margin_label)
        self.sale_price_input.valueChanged.connect(self._update_margin)
        self.purchase_price_input.valueChanged.connect(self._update_margin)

        self.quantity_input = SpinInput(minimum=1, maximum=MAX_QTY, value=1)
        pricing_fields.addRow("بڕ (دانە):", self.quantity_input)

        form_card.body.addLayout(pricing_fields)

        # ---- Dates ----
        form_card.body.addWidget(_section_label("بەروار"))
        date_fields = QFormLayout()
        date_fields.setVerticalSpacing(12)
        expiry_row = QHBoxLayout()
        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        self.expiry_input.setDisplayFormat("yyyy/MM/dd")
        self.expiry_input.setDate(QDate.currentDate().addYears(1))
        self.no_expiry_checkbox = QCheckBox("بەسەرچوون نییە")
        self.no_expiry_checkbox.stateChanged.connect(
            lambda state: self.expiry_input.setDisabled(bool(state))
        )
        expiry_row.addWidget(self.expiry_input)
        expiry_row.addWidget(self.no_expiry_checkbox)
        date_fields.addRow("بەرواری بەسەرچوون:", expiry_row)
        form_card.body.addLayout(date_fields)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        form_card.body.addWidget(self.error_label)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("پاشەکەوتکردن")
        self.save_btn.setIcon(icon("fa5s.check", "white"))
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.clear_btn = QPushButton("سڕینەوەی خانەکان")
        self.clear_btn.setProperty("secondary", True)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.reset_form)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.clear_btn)
        form_card.body.addLayout(btn_row)

        root.addWidget(form_card, 2)

        # ---- Left: product table ----
        table_card = Card("لیستی بەرهەمەکان")

        self.low_stock_label = QLabel("")
        self.low_stock_label.setProperty("role", "warning")
        self.low_stock_label.setWordWrap(True)
        table_card.body.addWidget(self.low_stock_label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("گەڕان بە ناو یان بارکۆد...")
        self.search_box.textChanged.connect(self.refresh_table)
        table_card.body.addWidget(self.search_box)

        self.data_table = DataTable(
            ["ناو", "بارکۆد", "نرخی فرۆشتن", "کۆی کۆگا", "نزیکترین بەسەرچوون"],
            empty_icon="fa5s.box-open",
            empty_text="هیچ بەرهەمێک تۆمار نەکراوە — لە فۆرمی لای ڕاست یەکێک زیاد بکە",
        )
        self.table = self.data_table.table
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(42)
        table_card.body.addWidget(self.data_table, 1)

        root.addWidget(table_card, 3)

    # -------------------------------------------------------------- margin
    def _update_margin(self):
        sale_price = self.sale_price_input.value()
        purchase_price = self.purchase_price_input.value()
        if sale_price <= 0:
            self.margin_label.setText("")
            return
        margin_pct = round((sale_price - purchase_price) / sale_price * 100)
        self.margin_label.setText(f"قازانج: {margin_pct}%")

    # ------------------------------------------------------------- actions
    def generate_barcode(self):
        self.barcode_input.setText(models.generate_local_barcode(self.conn))
        self.on_barcode_entered()

    def on_barcode_entered(self):
        barcode = self.barcode_input.text().strip()
        self.error_label.setText("")
        if not barcode:
            return

        product = models.find_product_by_barcode(self.conn, barcode)
        if product is None:
            self.existing_product = None
            self.mode_label.setText("بەرهەمی نوێ — زانیارییەکان پڕبکەوە")
            self.name_input.clear()
            self.category_input.clear()
            self.unit_input.setCurrentText("دانە")
            self.min_stock_input.setValue(5)
            self.sale_price_input.setValue(0)
            self.name_input.setEnabled(True)
            self.category_input.setEnabled(True)
            self.unit_input.setEnabled(True)
            self.min_stock_input.setEnabled(True)
            self.sale_price_input.setEnabled(self.user.is_admin or True)
            self.name_input.setFocus()
        else:
            self.existing_product = product
            self.mode_label.setText(
                f"بەرهەمی هەبوو: «{product['name']}» — تەنها زانیاری پڕکردنەوەی کۆگا پێویستە"
            )
            self.name_input.setText(product["name"])
            self.category_input.setText(product["category"] or "")
            self.unit_input.setCurrentText(product["unit"] or "دانە")
            self.min_stock_input.setValue(product["min_stock"] or 0)
            self.sale_price_input.setValue(product["sale_price"])
            # Restock mode: identity fields are locked, only batch info is editable
            self.name_input.setEnabled(False)
            self.category_input.setEnabled(False)
            self.unit_input.setEnabled(False)
            self.min_stock_input.setEnabled(False)
            self.sale_price_input.setEnabled(self.user.is_admin)
            self.purchase_price_input.spinbox.setFocus()
        self._update_margin()

    def on_save_clicked(self):
        """UI-facing slot: performs the save and shows a toast confirmation."""
        if self.save():
            show_toast(self.window(), "بەرهەم/کۆگا بە سەرکەوتوویی پاشەکەوت کرا", "success")
            self.reset_form()
            self.refresh_table()

    def save(self) -> bool:
        """Core save logic, with no dialogs — returns True on success. Safe to call headlessly."""
        self.error_label.setText("")
        barcode = self.barcode_input.text().strip()
        if not barcode:
            self.error_label.setText("تکایە بارکۆد بنووسە یان دروستی بکە")
            return False

        quantity = self.quantity_input.value()
        purchase_price = self.purchase_price_input.value()
        expiry_date = None if self.no_expiry_checkbox.isChecked() else self.expiry_input.date().toString("yyyy-MM-dd")

        try:
            if self.existing_product is not None:
                product_id = self.existing_product["id"]
                if self.user.is_admin:
                    new_sale_price = self.sale_price_input.value()
                    if new_sale_price != self.existing_product["sale_price"]:
                        models.update_product_sale_price(self.conn, product_id, new_sale_price)
            else:
                name = self.name_input.text().strip()
                if not name:
                    self.error_label.setText("تکایە ناوی بەرهەم بنووسە")
                    return False
                sale_price = self.sale_price_input.value()
                product_id = models.create_product(
                    self.conn,
                    name=name,
                    barcode=barcode,
                    category=self.category_input.text().strip() or None,
                    sale_price=sale_price,
                    unit=self.unit_input.currentText().strip() or "دانە",
                    min_stock=self.min_stock_input.value(),
                )

            models.add_stock_batch(
                self.conn,
                product_id=product_id,
                purchase_price=purchase_price,
                quantity=quantity,
                expiry_date=expiry_date,
            )
        except sqlite3.IntegrityError as exc:
            self.error_label.setText(f"هەڵە لە پاشەکەوتکردن: {exc}")
            return False

        return True

    def reset_form(self):
        self.existing_product = None
        self.barcode_input.clear()
        self.mode_label.setText("")
        self.name_input.clear()
        self.category_input.clear()
        self.unit_input.setCurrentText("دانە")
        self.min_stock_input.setValue(5)
        self.sale_price_input.setValue(0)
        self.purchase_price_input.setValue(0)
        self.quantity_input.setValue(1)
        self.no_expiry_checkbox.setChecked(False)
        self.expiry_input.setDate(QDate.currentDate().addYears(1))
        self.name_input.setEnabled(True)
        self.category_input.setEnabled(True)
        self.unit_input.setEnabled(True)
        self.min_stock_input.setEnabled(True)
        self.sale_price_input.setEnabled(True)
        self.error_label.setText("")
        self.margin_label.setText("")
        self.barcode_input.setFocus()

    def refresh_table(self):
        products = models.list_products_with_stock(self.conn)
        query = self.search_box.text().strip().lower()
        if query:
            products = [
                p for p in products
                if query in p["name"].lower() or query in p["barcode"].lower()
            ]

        self.table.setRowCount(len(products))
        for row, p in enumerate(products):
            self.table.setItem(row, 0, QTableWidgetItem(p["name"]))
            for col, text in (
                (1, p["barcode"]),
                (2, f"{p['sale_price']:,} د.ع"),
                (3, str(p["total_stock"])),
                (4, p["nearest_expiry"] or "—"),
            ):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, item)

        low_stock = models.list_low_stock_products(self.conn)
        if low_stock:
            names = "، ".join(p["name"] for p in low_stock)
            self.low_stock_label.setText(f"⚠ ئاگاداری کەمی کۆگا: {names}")
        else:
            self.low_stock_label.setText("")

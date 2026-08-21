"""Product entry screen: barcode scan -> new product form OR restock (new batch) form."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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

MAX_PRICE = 999_999_999
MAX_QTY = 1_000_000


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

        # ---- Left: form ----
        form_box = QGroupBox("زیادکردنی بەرهەم / پڕکردنەوەی کۆگا")
        apply_card_shadow(form_box)
        form_layout = QVBoxLayout(form_box)
        form_layout.setSpacing(16)

        barcode_row = QHBoxLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setObjectName("barcodeInput")
        self.barcode_input.setPlaceholderText("بارکۆد سکان بکە یان بنووسە و Enter دابگرە")
        self.barcode_input.returnPressed.connect(self.on_barcode_entered)
        barcode_row.addWidget(QLabel("بارکۆد:"))
        barcode_row.addWidget(self.barcode_input)
        self.gen_barcode_btn = QPushButton("دروستکردنی بارکۆدی ناوخۆیی")
        self.gen_barcode_btn.setIcon(icon("fa5s.barcode", Colors.TEXT_SECONDARY))
        self.gen_barcode_btn.setProperty("secondary", True)
        self.gen_barcode_btn.clicked.connect(self.generate_barcode)
        barcode_row.addWidget(self.gen_barcode_btn)
        form_layout.addLayout(barcode_row)

        self.mode_label = QLabel("")
        self.mode_label.setProperty("role", "warning")
        self.mode_label.setWordWrap(True)
        form_layout.addWidget(self.mode_label)

        fields = QFormLayout()
        fields.setSpacing(12)
        fields.setVerticalSpacing(12)
        self.name_input = QLineEdit()
        fields.addRow("ناوی بەرهەم:", self.name_input)

        self.category_input = QLineEdit()
        fields.addRow("جۆر:", self.category_input)

        self.unit_input = QComboBox()
        self.unit_input.setEditable(True)
        self.unit_input.addItems(["دانە", "کیلۆگرام", "لیتر", "پاکەت", "کارتۆن"])
        fields.addRow("یەکە:", self.unit_input)

        self.min_stock_input = QSpinBox()
        self.min_stock_input.setRange(0, MAX_QTY)
        self.min_stock_input.setValue(5)
        fields.addRow("کەمترین ڕادەی کۆگا:", self.min_stock_input)

        self.sale_price_input = QSpinBox()
        self.sale_price_input.setRange(0, MAX_PRICE)
        self.sale_price_input.setSuffix(" د.ع")
        fields.addRow("نرخی فرۆشتن:", self.sale_price_input)

        self.purchase_price_input = QSpinBox()
        self.purchase_price_input.setRange(0, MAX_PRICE)
        self.purchase_price_input.setSuffix(" د.ع")
        fields.addRow("نرخی کڕین:", self.purchase_price_input)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, MAX_QTY)
        self.quantity_input.setValue(1)
        fields.addRow("بڕ (دانە):", self.quantity_input)

        expiry_row = QHBoxLayout()
        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        self.expiry_input.setDate(QDate.currentDate().addYears(1))
        self.no_expiry_checkbox = QCheckBox("بەسەرچوون نییە")
        self.no_expiry_checkbox.stateChanged.connect(
            lambda state: self.expiry_input.setDisabled(bool(state))
        )
        expiry_row.addWidget(self.expiry_input)
        expiry_row.addWidget(self.no_expiry_checkbox)
        fields.addRow("بەرواری بەسەرچوون:", expiry_row)

        form_layout.addLayout(fields)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        form_layout.addWidget(self.error_label)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("پاشەکەوتکردن")
        self.save_btn.setIcon(icon("fa5s.check", "white"))
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.clear_btn = QPushButton("سڕینەوەی خانەکان")
        self.clear_btn.setProperty("secondary", True)
        self.clear_btn.clicked.connect(self.reset_form)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.clear_btn)
        form_layout.addLayout(btn_row)

        form_layout.addStretch()
        root.addWidget(form_box, 2)

        # ---- Right: product table ----
        table_box = QGroupBox("لیستی بەرهەمەکان")
        apply_card_shadow(table_box)
        table_layout = QVBoxLayout(table_box)
        table_layout.setSpacing(12)

        self.low_stock_label = QLabel("")
        self.low_stock_label.setProperty("role", "warning")
        self.low_stock_label.setWordWrap(True)
        table_layout.addWidget(self.low_stock_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ناو", "بارکۆد", "نرخی فرۆشتن", "کۆی کۆگا", "نزیکترین بەسەرچوون"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setMouseTracking(True)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.verticalHeader().setVisible(False)
        table_layout.addWidget(self.table)

        root.addWidget(table_box, 3)

        # Cashiers cannot change sale price on an existing product; they can still
        # set it for a brand-new product they are entering.
        if not self.user.is_admin:
            pass  # enforced dynamically in on_barcode_entered

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
            self.purchase_price_input.setFocus()

    def on_save_clicked(self):
        """UI-facing slot: performs the save and shows a blocking confirmation dialog."""
        if self.save():
            QMessageBox.information(self, "سەرکەوتوو", "بەرهەم/کۆگا بە سەرکەوتوویی پاشەکەوت کرا")
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
        self.barcode_input.setFocus()

    def refresh_table(self):
        products = models.list_products_with_stock(self.conn)
        self.table.setRowCount(len(products))
        for row, p in enumerate(products):
            self.table.setItem(row, 0, QTableWidgetItem(p["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(p["barcode"]))
            self.table.setItem(row, 2, QTableWidgetItem(f"{p['sale_price']:,} د.ع"))
            self.table.setItem(row, 3, QTableWidgetItem(str(p["total_stock"])))
            self.table.setItem(row, 4, QTableWidgetItem(p["nearest_expiry"] or "—"))

        low_stock = models.list_low_stock_products(self.conn)
        if low_stock:
            names = "، ".join(p["name"] for p in low_stock)
            self.low_stock_label.setText(f"⚠ ئاگاداری کەمی کۆگا: {names}")
        else:
            self.low_stock_label.setText("")

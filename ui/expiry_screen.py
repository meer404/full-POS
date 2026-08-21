"""Expiry management screen (admin only): expired batches + soon-to-expire warnings."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import models
from ui.style import Colors, apply_card_shadow, icon

WARNING_DAYS = 7
WARNING_COLOR = Colors.WARNING_BG
DANGER_COLOR = Colors.DANGER_BG


class ExpiryScreen(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        expired_box = QGroupBox("بەرهەمە بەسەرچووەکان")
        apply_card_shadow(expired_box)
        expired_layout = QVBoxLayout(expired_box)
        self.expired_table = QTableWidget(0, 6)
        self.expired_table.setHorizontalHeaderLabels(
            ["بەرهەم", "بڕ", "بەرواری بەسەرچوون", "نرخی کڕین", "زیانی مامەڵە", "بژاردەکان"]
        )
        self.expired_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.expired_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.expired_table.setMouseTracking(True)
        self.expired_table.verticalHeader().setDefaultSectionSize(42)
        self.expired_table.verticalHeader().setVisible(False)
        expired_layout.addWidget(self.expired_table)
        root.addWidget(expired_box)

        warning_box = QGroupBox(f"ئاگاداری: نزیکن لە بەسەرچوون (کەمتر یان یەکسان بە {WARNING_DAYS} ڕۆژ)")
        apply_card_shadow(warning_box)
        warning_layout = QVBoxLayout(warning_box)
        self.warning_table = QTableWidget(0, 3)
        self.warning_table.setHorizontalHeaderLabels(["بەرهەم", "بڕ", "بەرواری بەسەرچوون"])
        self.warning_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.warning_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.warning_table.setMouseTracking(True)
        self.warning_table.verticalHeader().setDefaultSectionSize(38)
        self.warning_table.verticalHeader().setVisible(False)
        warning_layout.addWidget(self.warning_table)
        root.addWidget(warning_box)

    # ------------------------------------------------------------- actions
    def mark_as_loss(self, batch_id: int):
        models.dispose_batch(self.conn, batch_id, reason="expired")
        self.refresh()

    def return_to_supplier(self, batch_id: int):
        models.dispose_batch(self.conn, batch_id, reason="supplier_return")
        self.refresh()

    def on_mark_as_loss_clicked(self, batch_id: int):
        self.mark_as_loss(batch_id)
        QMessageBox.information(self, "تۆمارکرا", "وەک زیان تۆمارکرا")

    def on_return_to_supplier_clicked(self, batch_id: int):
        self.return_to_supplier(batch_id)
        QMessageBox.information(self, "تۆمارکرا", "گەڕایەوە بۆ دابینکەر")

    # ------------------------------------------------------------- refresh
    def refresh(self):
        today = date.today().isoformat()
        warn_date = (date.today() + timedelta(days=WARNING_DAYS)).isoformat()

        expired = models.list_expired_batches(self.conn, today)
        self.expired_table.setRowCount(len(expired))
        for row, b in enumerate(expired):
            name_item = QTableWidgetItem(b["product_name"])
            qty_item = QTableWidgetItem(f"{b['quantity']} {b['unit']}")
            date_item = QTableWidgetItem(b["expiry_date"])
            loss_value = b["purchase_price"] * b["quantity"]
            price_item = QTableWidgetItem(f"{b['purchase_price']:,} د.ع")
            loss_item = QTableWidgetItem(f"{loss_value:,} د.ع")
            for item in (name_item, qty_item, date_item, price_item, loss_item):
                item.setBackground(QColor(DANGER_COLOR))
            self.expired_table.setItem(row, 0, name_item)
            self.expired_table.setItem(row, 1, qty_item)
            self.expired_table.setItem(row, 2, date_item)
            self.expired_table.setItem(row, 3, price_item)
            self.expired_table.setItem(row, 4, loss_item)

            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            loss_btn = QPushButton(" زیان")
            loss_btn.setIcon(icon("fa5s.trash-alt", "white"))
            loss_btn.setProperty("danger", True)
            loss_btn.clicked.connect(lambda _, bid=b["id"]: self.on_mark_as_loss_clicked(bid))
            return_btn = QPushButton(" گەڕانەوە")
            return_btn.setIcon(icon("fa5s.undo", Colors.TEXT_SECONDARY))
            return_btn.setProperty("secondary", True)
            return_btn.clicked.connect(lambda _, bid=b["id"]: self.on_return_to_supplier_clicked(bid))
            actions_layout.addWidget(loss_btn)
            actions_layout.addWidget(return_btn)
            self.expired_table.setCellWidget(row, 5, actions)

        soon = models.list_expiring_soon_batches(self.conn, today, warn_date)
        self.warning_table.setRowCount(len(soon))
        for row, b in enumerate(soon):
            name_item = QTableWidgetItem(b["product_name"])
            qty_item = QTableWidgetItem(f"{b['quantity']} {b['unit']}")
            date_item = QTableWidgetItem(b["expiry_date"])
            for item in (name_item, qty_item, date_item):
                item.setBackground(QColor(WARNING_COLOR))
            self.warning_table.setItem(row, 0, name_item)
            self.warning_table.setItem(row, 1, qty_item)
            self.warning_table.setItem(row, 2, date_item)

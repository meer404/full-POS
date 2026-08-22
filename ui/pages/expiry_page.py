"""Expiry management screen (admin only): expired batches + soon-to-expire warnings."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import models
from ui.theme import Colors, icon
from ui.widgets.data_table import DataTable
from ui.widgets.toast import confirm, show_toast

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

        self.tabs = QTabWidget()

        expired_tab = QWidget()
        expired_layout = QVBoxLayout(expired_tab)
        self.expired_data_table = DataTable(
            ["بەرهەم", "بڕ", "بەرواری بەسەرچوون", "نرخی کڕین", "زیانی مامەڵە", "بژاردەکان"],
            empty_icon="fa5s.check-circle",
            empty_text="هیچ بەرهەمێکی بەسەرچوو نییە",
        )
        self.expired_table = self.expired_data_table.table
        self.expired_table.setObjectName("expiredTable")
        expired_header = self.expired_table.horizontalHeader()
        expired_header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3, 4):
            expired_header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        expired_header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.expired_table.setColumnWidth(5, 200)
        self.expired_table.setSelectionMode(QAbstractItemView.NoSelection)
        expired_layout.addWidget(self.expired_data_table)
        self.tabs.addTab(expired_tab, "بەسەرچووەکان")

        warning_tab = QWidget()
        warning_layout = QVBoxLayout(warning_tab)
        self.warning_data_table = DataTable(
            ["بەرهەم", "بڕ", "بەرواری بەسەرچوون"],
            empty_icon="fa5s.check-circle",
            empty_text="هیچ بەرهەمێک نزیک نییە لە بەسەرچوون",
        )
        self.warning_table = self.warning_data_table.table
        self.warning_table.setObjectName("warningTable")
        warning_header = self.warning_table.horizontalHeader()
        warning_header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2):
            warning_header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.warning_table.setSelectionMode(QAbstractItemView.NoSelection)
        warning_layout.addWidget(self.warning_data_table)
        self.tabs.addTab(warning_tab, f"ئاگاداری (کەمتر یان یەکسان بە {WARNING_DAYS} ڕۆژ)")

        root.addWidget(self.tabs)

    # ------------------------------------------------------------- actions
    def mark_as_loss(self, batch_id: int):
        models.dispose_batch(self.conn, batch_id, reason="expired")
        self.refresh()

    def return_to_supplier(self, batch_id: int):
        models.dispose_batch(self.conn, batch_id, reason="supplier_return")
        self.refresh()

    def on_mark_as_loss_clicked(self, batch_id: int):
        if confirm(self, "دڵنیایت لەوەی ئەم بەرهەمە وەک زیان تۆمار بکەیت؟ ئەم کردارە ناگەڕێتەوە."):
            self.mark_as_loss(batch_id)
            show_toast(self.window(), "وەک زیان تۆمارکرا", "success")

    def on_return_to_supplier_clicked(self, batch_id: int):
        if confirm(self, "دڵنیایت لەوەی ئەم بەرهەمە بگەڕێنیتەوە بۆ دابینکەر؟"):
            self.return_to_supplier(batch_id)
            show_toast(self.window(), "گەڕایەوە بۆ دابینکەر", "success")

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
            for item in (qty_item, date_item, price_item, loss_item):
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
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
            loss_btn.setCursor(Qt.PointingHandCursor)
            loss_btn.clicked.connect(lambda _, bid=b["id"]: self.on_mark_as_loss_clicked(bid))
            return_btn = QPushButton(" گەڕانەوە")
            return_btn.setIcon(icon("fa5s.undo", Colors.TEXT_SECONDARY))
            return_btn.setProperty("secondary", True)
            return_btn.setCursor(Qt.PointingHandCursor)
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
            for item in (qty_item, date_item):
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            for item in (name_item, qty_item, date_item):
                item.setBackground(QColor(WARNING_COLOR))
            self.warning_table.setItem(row, 0, name_item)
            self.warning_table.setItem(row, 1, qty_item)
            self.warning_table.setItem(row, 2, date_item)

        self.tabs.setTabText(0, f"بەسەرچووەکان ({len(expired)})")
        self.tabs.setTabText(1, f"ئاگاداری ({len(soon)})")

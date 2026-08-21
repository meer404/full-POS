"""Reports screen (admin only): daily / weekly / monthly sales & profit summaries."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import models

PERIOD_DAILY = "ڕۆژانە"
PERIOD_WEEKLY = "هەفتانە"
PERIOD_MONTHLY = "مانگانە"


class ReportsScreen(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("ماوە:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems([PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY])
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        filter_row.addWidget(self.period_combo)

        filter_row.addWidget(QLabel("لە:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        filter_row.addWidget(self.start_date)

        filter_row.addWidget(QLabel("بۆ:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        filter_row.addWidget(self.end_date)

        self.refresh_btn = QPushButton("نوێکردنەوە")
        self.refresh_btn.clicked.connect(self.refresh)
        filter_row.addWidget(self.refresh_btn)
        filter_row.addStretch()

        root.addLayout(filter_row)

        stats_box = QGroupBox("پوختەی فرۆشتن")
        stats_grid = QGridLayout(stats_box)
        self.receipt_count_label = QLabel("0")
        self.qty_label = QLabel("0")
        self.revenue_label = QLabel("0 د.ع")
        self.profit_label = QLabel("0 د.ع")
        for lbl in (self.receipt_count_label, self.qty_label, self.revenue_label, self.profit_label):
            lbl.setProperty("role", "total")

        stats_grid.addWidget(QLabel("ژمارەی پسوڵەکان:"), 0, 0)
        stats_grid.addWidget(self.receipt_count_label, 0, 1)
        stats_grid.addWidget(QLabel("کۆی دانە فرۆشراو:"), 0, 2)
        stats_grid.addWidget(self.qty_label, 0, 3)
        stats_grid.addWidget(QLabel("کۆی داهات:"), 1, 0)
        stats_grid.addWidget(self.revenue_label, 1, 1)
        stats_grid.addWidget(QLabel("کۆی قازانج:"), 1, 2)
        stats_grid.addWidget(self.profit_label, 1, 3)
        root.addWidget(stats_box)

        top_box = QGroupBox("باشترین 5 بەرهەمی فرۆشراو")
        top_layout = QVBoxLayout(top_box)
        self.top_table = QTableWidget(0, 2)
        self.top_table.setHorizontalHeaderLabels(["بەرهەم", "دانەی فرۆشراو"])
        self.top_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.top_table.setEditTriggers(QTableWidget.NoEditTriggers)
        top_layout.addWidget(self.top_table)
        root.addWidget(top_box)

        self.on_period_changed(self.period_combo.currentText())

    def on_period_changed(self, period: str):
        today = QDate.currentDate()
        if period == PERIOD_DAILY:
            self.start_date.setDate(today)
            self.end_date.setDate(today)
        elif period == PERIOD_WEEKLY:
            self.start_date.setDate(today.addDays(-6))
            self.end_date.setDate(today)
        elif period == PERIOD_MONTHLY:
            self.start_date.setDate(today.addDays(-29))
            self.end_date.setDate(today)
        self.refresh()

    def refresh(self):
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")
        report = models.sales_report(self.conn, start, end)

        self.receipt_count_label.setText(str(report["receipt_count"]))
        self.qty_label.setText(str(report["total_qty"]))
        self.revenue_label.setText(f"{report['total_revenue']:,} د.ع")
        self.profit_label.setText(f"{report['total_profit']:,} د.ع")

        self.top_table.setRowCount(len(report["top_products"]))
        for row, p in enumerate(report["top_products"]):
            self.top_table.setItem(row, 0, QTableWidgetItem(p["name"]))
            self.top_table.setItem(row, 1, QTableWidgetItem(str(p["qty"])))

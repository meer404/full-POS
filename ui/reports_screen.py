"""Reports screen (admin only): daily / weekly / monthly sales & profit summaries."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate, QSize
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
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
from ui.style import Colors, apply_card_shadow, icon

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
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        filter_card = QGroupBox()
        apply_card_shadow(filter_card)
        filter_row = QHBoxLayout(filter_card)
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

        self.refresh_btn = QPushButton(" نوێکردنەوە")
        self.refresh_btn.setIcon(icon("fa5s.sync-alt", "white"))
        self.refresh_btn.clicked.connect(self.refresh)
        filter_row.addWidget(self.refresh_btn)
        filter_row.addStretch()

        root.addWidget(filter_card)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        self.receipt_count_label = QLabel("0")
        self.qty_label = QLabel("0")
        self.revenue_label = QLabel("0 د.ع")
        self.profit_label = QLabel("0 د.ع")

        stats_row.addWidget(self._stat_tile("fa5s.receipt", "ژمارەی پسوڵەکان", self.receipt_count_label, Colors.SECONDARY))
        stats_row.addWidget(self._stat_tile("fa5s.box", "کۆی دانە فرۆشراو", self.qty_label, Colors.SECONDARY))
        stats_row.addWidget(self._stat_tile("fa5s.coins", "کۆی داهات", self.revenue_label, Colors.PRIMARY))
        stats_row.addWidget(self._stat_tile("fa5s.chart-line", "کۆی قازانج", self.profit_label, Colors.PRIMARY))
        root.addLayout(stats_row)

        top_box = QGroupBox("باشترین 5 بەرهەمی فرۆشراو")
        apply_card_shadow(top_box)
        top_layout = QVBoxLayout(top_box)
        self.top_table = QTableWidget(0, 2)
        self.top_table.setHorizontalHeaderLabels(["بەرهەم", "دانەی فرۆشراو"])
        self.top_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.top_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.top_table.setAlternatingRowColors(True)
        self.top_table.setMouseTracking(True)
        self.top_table.verticalHeader().setDefaultSectionSize(36)
        self.top_table.verticalHeader().setVisible(False)
        top_layout.addWidget(self.top_table)
        root.addWidget(top_box)

        self.on_period_changed(self.period_combo.currentText())

    @staticmethod
    def _stat_tile(icon_name: str, caption: str, value_label: QLabel, accent: str) -> QFrame:
        tile = QFrame()
        tile.setObjectName("card")
        apply_card_shadow(tile)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name, accent).pixmap(QSize(22, 22)))
        layout.addWidget(icon_label)

        value_label.setProperty("role", "total")
        layout.addWidget(value_label)

        caption_label = QLabel(caption)
        caption_label.setProperty("role", "caption")
        layout.addWidget(caption_label)

        return tile

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

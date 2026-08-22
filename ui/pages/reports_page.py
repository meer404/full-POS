"""Reports screen (admin only): daily / weekly / monthly sales & profit summaries."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import models
from ui.theme import Colors, icon
from ui.widgets.card import Card
from ui.widgets.data_table import DataTable
from ui.widgets.stat_card import StatCard

PERIOD_DAILY = "ڕۆژانە"
PERIOD_WEEKLY = "هەفتانە"
PERIOD_MONTHLY = "مانگانە"


class ReportsScreen(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._period_buttons: dict[str, QPushButton] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        filter_card = Card()
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        filter_row.addWidget(QLabel("ماوە:"))
        group = QButtonGroup(self)
        group.setExclusive(True)
        for period in (PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY):
            btn = QPushButton(period)
            btn.setProperty("segment", True)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, p=period: self.set_period(p))
            group.addButton(btn)
            self._period_buttons[period] = btn
            filter_row.addWidget(btn)

        filter_row.addWidget(QLabel("لە:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy/MM/dd")
        self.start_date.setDate(QDate.currentDate())
        filter_row.addWidget(self.start_date)

        filter_row.addWidget(QLabel("بۆ:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy/MM/dd")
        self.end_date.setDate(QDate.currentDate())
        filter_row.addWidget(self.end_date)

        self.refresh_btn = QPushButton(" نوێکردنەوە")
        self.refresh_btn.setIcon(icon("fa5s.sync-alt", "white"))
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        filter_row.addWidget(self.refresh_btn)
        filter_row.addStretch()

        filter_card.body.addLayout(filter_row)
        root.addWidget(filter_card)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)
        self.receipt_stat = StatCard("fa5s.receipt", "ژمارەی پسوڵەکان", Colors.SECONDARY)
        self.qty_stat = StatCard("fa5s.box", "کۆی دانە فرۆشراو", Colors.ROLE_ADMIN)
        self.revenue_stat = StatCard("fa5s.coins", "کۆی داهات", Colors.PRIMARY)
        self.profit_stat = StatCard("fa5s.chart-line", "کۆی قازانج", Colors.WARNING)
        stats_grid.addWidget(self.receipt_stat, 0, 0)
        stats_grid.addWidget(self.qty_stat, 0, 1)
        stats_grid.addWidget(self.revenue_stat, 1, 0)
        stats_grid.addWidget(self.profit_stat, 1, 1)
        root.addLayout(stats_grid)

        top_card = Card("باشترین 5 بەرهەمی فرۆشراو")
        self.top_data_table = DataTable(
            ["بەرهەم", "دانەی فرۆشراو"],
            empty_icon="fa5s.chart-bar",
            empty_text="هێشتا هیچ فرۆشتنێک لەم ماوەیەدا نەکراوە",
        )
        self.top_table = self.top_data_table.table
        self.top_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        top_card.body.addWidget(self.top_data_table)
        root.addWidget(top_card, 1)

        self.set_period(PERIOD_DAILY)

    def current_period(self) -> str:
        for period, btn in self._period_buttons.items():
            if btn.isChecked():
                return period
        return PERIOD_DAILY

    def set_period(self, period: str):
        self._period_buttons[period].setChecked(True)
        self.on_period_changed(period)

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

        self.receipt_stat.set_value(str(report["receipt_count"]))
        self.qty_stat.set_value(str(report["total_qty"]))
        self.revenue_stat.set_value(f"{report['total_revenue']:,} د.ع")
        self.profit_stat.set_value(f"{report['total_profit']:,} د.ع")

        self.top_table.setRowCount(len(report["top_products"]))
        for row, p in enumerate(report["top_products"]):
            self.top_table.setItem(row, 0, QTableWidgetItem(p["name"]))
            qty_item = QTableWidgetItem(str(p["qty"]))
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.top_table.setItem(row, 1, qty_item)

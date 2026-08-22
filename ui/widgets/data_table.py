"""DataTable: a QTableWidget preconfigured to the app's table look (no grid, zebra rows, row
hover, 48px rows, sticky header) wrapped in a QStackedWidget with an EmptyState page.

Screens keep using `data_table.table.setRowCount(...)` / `.setItem(...)` exactly like they used
a bare `self.table` before — this widget watches the table's row count and swaps to the empty
state automatically, no extra calls needed at the call site.
"""
from __future__ import annotations

from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QStackedWidget, QTableWidget

from ui.widgets.empty_state import EmptyState


class DataTable(QStackedWidget):
    def __init__(
        self,
        columns: list[str],
        empty_icon: str = "fa5s.inbox",
        empty_text: str = "هیچ داتایەک نییە",
        empty_action_label: str | None = None,
        on_empty_action=None,
        parent=None,
    ):
        super().__init__(parent)

        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setMouseTracking(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.horizontalHeader().setFixedHeight(44)

        self._empty = EmptyState(empty_icon, empty_text, empty_action_label, on_empty_action)

        self.addWidget(self.table)
        self.addWidget(self._empty)

        self.table.model().rowsInserted.connect(self._sync)
        self.table.model().rowsRemoved.connect(self._sync)
        self._sync()

    def _sync(self, *_args):
        self.setCurrentWidget(self._empty if self.table.rowCount() == 0 else self.table)

"""User management screen (admin only): add/remove users, change passwords."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidgetItem,
    QWidget,
)

import auth
from ui.theme import Colors, icon
from ui.widgets.badge import Badge
from ui.widgets.card import Card
from ui.widgets.data_table import DataTable
from ui.widgets.toast import confirm, show_toast


class UsersScreen(QWidget):
    def __init__(self, conn: sqlite3.Connection, current_user: auth.User, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        form_card = Card("زیادکردنی بەکارهێنەری نوێ")
        form_card.setMinimumWidth(340)
        fields = QFormLayout()
        fields.setVerticalSpacing(12)

        self.username_input = QLineEdit()
        fields.addRow("ناوی بەکارهێنەر:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        fields.addRow("وشەی نهێنی:", self.password_input)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["cashier", "admin"])
        fields.addRow("ڕۆڵ:", self.role_combo)

        form_card.body.addLayout(fields)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        form_card.body.addWidget(self.error_label)

        self.add_btn = QPushButton(" زیادکردن")
        self.add_btn.setIcon(icon("fa5s.user-plus", "white"))
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.on_add_clicked)
        form_card.body.addWidget(self.add_btn)

        section_label = QLabel("گۆڕینی وشەی نهێنی (بۆ بەکارهێنەری دیاریکراو)")
        section_label.setProperty("role", "section")
        form_card.body.addWidget(section_label)
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setPlaceholderText("وشەی نهێنی نوێ")
        form_card.body.addWidget(self.new_password_input)
        self.change_password_btn = QPushButton(" گۆڕینی وشەی نهێنی")
        self.change_password_btn.setIcon(icon("fa5s.key", Colors.TEXT_SECONDARY))
        self.change_password_btn.setProperty("secondary", True)
        self.change_password_btn.setCursor(Qt.PointingHandCursor)
        self.change_password_btn.clicked.connect(self.on_change_password_clicked)
        form_card.body.addWidget(self.change_password_btn)

        root.addWidget(form_card, 2)

        table_card = Card("بەکارهێنەرەکان")
        self.data_table = DataTable(
            ["ناو", "ڕۆڵ", "بژاردەکان"],
            empty_icon="fa5s.users",
            empty_text="هیچ بەکارهێنەرێک نییە",
        )
        self.table = self.data_table.table
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        table_card.body.addWidget(self.data_table, 1)
        root.addWidget(table_card, 3)

        self.selected_user_id: int | None = None

    # ------------------------------------------------------------- actions
    def on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.selected_user_id = None
            return
        row = rows[0].row()
        self.selected_user_id = self.table.item(row, 0).data(Qt.UserRole)

    def add_user(self, username: str, password: str, role: str) -> bool:
        """Core logic, no dialogs. Returns True on success, sets error_label otherwise."""
        self.error_label.setText("")
        username = username.strip()
        if not username or not password:
            self.error_label.setText("تکایە ناو و وشەی نهێنی پڕبکەوە")
            return False
        try:
            auth.create_user(self.conn, username, password, role)
        except sqlite3.IntegrityError:
            self.error_label.setText("ئەم ناوە بەکارهێنراوە، ناوێکی تر هەڵبژێرە")
            return False
        return True

    def on_add_clicked(self):
        if self.add_user(self.username_input.text(), self.password_input.text(), self.role_combo.currentText()):
            self.username_input.clear()
            self.password_input.clear()
            self.refresh_table()
            show_toast(self.window(), "بەکارهێنەر زیادکرا", "success")

    def remove_user(self, user_id: int) -> bool:
        if user_id == self.current_user.id:
            self.error_label.setText("ناتوانیت خۆت بسڕیتەوە")
            return False
        auth.delete_user(self.conn, user_id)
        return True

    def on_remove_clicked(self, user_id: int, username: str):
        if not confirm(self, f"دڵنیایت لەوەی بەکارهێنەری «{username}» بسڕیتەوە؟"):
            return
        if self.remove_user(user_id):
            self.refresh_table()
            show_toast(self.window(), "بەکارهێنەر سڕایەوە", "success")

    def change_password(self, user_id: int, new_password: str) -> bool:
        self.error_label.setText("")
        if not new_password:
            self.error_label.setText("تکایە وشەی نهێنی نوێ بنووسە")
            return False
        auth.change_password(self.conn, user_id, new_password)
        return True

    def on_change_password_clicked(self):
        if self.selected_user_id is None:
            self.error_label.setText("تکایە بەکارهێنەرێک لە خشتەکە هەڵبژێرە")
            return
        if self.change_password(self.selected_user_id, self.new_password_input.text()):
            self.new_password_input.clear()
            show_toast(self.window(), "وشەی نهێنی گۆڕدرا", "success")

    # ------------------------------------------------------------- refresh
    def refresh_table(self):
        users = auth.list_users(self.conn)
        self.table.setRowCount(len(users))
        for row, u in enumerate(users):
            name_item = QTableWidgetItem(u["username"])
            name_item.setData(Qt.UserRole, u["id"])
            self.table.setItem(row, 0, name_item)

            role_badge = Badge("بەڕێوەبەر" if u["role"] == "admin" else "فرۆشیار", u["role"])
            self.table.setCellWidget(row, 1, role_badge)

            remove_btn = QPushButton(" سڕینەوە")
            remove_btn.setIcon(icon("fa5s.trash-alt", "white"))
            remove_btn.setProperty("danger", True)
            is_self = u["id"] == self.current_user.id
            if is_self:
                remove_btn.setEnabled(False)
                remove_btn.setToolTip("ناتوانیت خۆت بسڕیتەوە")
            else:
                remove_btn.setCursor(Qt.PointingHandCursor)
                remove_btn.clicked.connect(
                    lambda _, uid=u["id"], name=u["username"]: self.on_remove_clicked(uid, name)
                )
            self.table.setCellWidget(row, 2, remove_btn)

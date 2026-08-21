"""User management screen (admin only): add/remove users, change passwords."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import auth


class UsersScreen(QWidget):
    def __init__(self, conn: sqlite3.Connection, current_user: auth.User, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        root = QHBoxLayout(self)

        form_box = QGroupBox("زیادکردنی بەکارهێنەری نوێ")
        form_layout = QVBoxLayout(form_box)
        fields = QFormLayout()

        self.username_input = QLineEdit()
        fields.addRow("ناوی بەکارهێنەر:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        fields.addRow("وشەی نهێنی:", self.password_input)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["cashier", "admin"])
        fields.addRow("ڕۆڵ:", self.role_combo)

        form_layout.addLayout(fields)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        form_layout.addWidget(self.error_label)

        self.add_btn = QPushButton("زیادکردن")
        self.add_btn.clicked.connect(self.on_add_clicked)
        form_layout.addWidget(self.add_btn)

        form_layout.addSpacing(20)
        form_layout.addWidget(QLabel("گۆڕینی وشەی نهێنی (بۆ بەکارهێنەری دیاریکراو):"))
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setPlaceholderText("وشەی نهێنی نوێ")
        form_layout.addWidget(self.new_password_input)
        self.change_password_btn = QPushButton("گۆڕینی وشەی نهێنی")
        self.change_password_btn.clicked.connect(self.on_change_password_clicked)
        form_layout.addWidget(self.change_password_btn)

        form_layout.addStretch()
        root.addWidget(form_box, 2)

        table_box = QGroupBox("بەکارهێنەرەکان")
        table_layout = QVBoxLayout(table_box)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ناو", "ڕۆڵ", "بژاردەکان"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        table_layout.addWidget(self.table)
        root.addWidget(table_box, 3)

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
            QMessageBox.information(self, "سەرکەوتوو", "بەکارهێنەر زیادکرا")

    def remove_user(self, user_id: int) -> bool:
        if user_id == self.current_user.id:
            self.error_label.setText("ناتوانیت خۆت بسڕیتەوە")
            return False
        auth.delete_user(self.conn, user_id)
        return True

    def on_remove_clicked(self, user_id: int):
        if self.remove_user(user_id):
            self.refresh_table()

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
            QMessageBox.information(self, "سەرکەوتوو", "وشەی نهێنی گۆڕدرا")

    # ------------------------------------------------------------- refresh
    def refresh_table(self):
        users = auth.list_users(self.conn)
        self.table.setRowCount(len(users))
        for row, u in enumerate(users):
            name_item = QTableWidgetItem(u["username"])
            name_item.setData(Qt.UserRole, u["id"])
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(u["role"]))

            remove_btn = QPushButton("سڕینەوە")
            remove_btn.setProperty("danger", True)
            remove_btn.clicked.connect(lambda _, uid=u["id"]: self.on_remove_clicked(uid))
            self.table.setCellWidget(row, 2, remove_btn)

"""Shared visual style for the whole application (RTL, fonts, colors)."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

APP_FONT_FAMILY = "Segoe UI"
BASE_FONT_SIZE = 11

STYLESHEET = """
* {
    font-family: 'Segoe UI', Tahoma, sans-serif;
    font-size: 11pt;
}
QWidget {
    background-color: #f4f5f7;
    color: #1f2430;
}
QMainWindow, QDialog {
    background-color: #f4f5f7;
}
QPushButton {
    background-color: #2f6fed;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover { background-color: #245bcc; }
QPushButton:pressed { background-color: #1c48a3; }
QPushButton:disabled { background-color: #a9b4c9; }
QPushButton[danger="true"] { background-color: #d64545; }
QPushButton[danger="true"]:hover { background-color: #b83636; }
QPushButton[secondary="true"] { background-color: #6b7280; }
QPushButton[secondary="true"]:hover { background-color: #4b5563; }
QLineEdit, QComboBox, QDateEdit, QSpinBox {
    background-color: white;
    border: 1px solid #cbd2e1;
    border-radius: 5px;
    padding: 6px 8px;
    min-height: 22px;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus {
    border: 1px solid #2f6fed;
}
QTableWidget {
    background-color: white;
    border: 1px solid #dde1ea;
    gridline-color: #eef0f4;
    selection-background-color: #dbe7ff;
    selection-color: #1f2430;
}
QHeaderView::section {
    background-color: #eaedf3;
    padding: 6px;
    border: none;
    font-weight: 600;
}
QTabWidget::pane {
    border: 1px solid #dde1ea;
    background: #f4f5f7;
}
QTabBar::tab {
    background: #e3e6ec;
    padding: 10px 18px;
    margin: 2px;
    border-radius: 6px;
}
QTabBar::tab:selected {
    background: #2f6fed;
    color: white;
    font-weight: 600;
}
QLabel[role="title"] {
    font-size: 16pt;
    font-weight: 700;
}
QLabel[role="total"] {
    font-size: 22pt;
    font-weight: 800;
    color: #17803c;
}
QLabel[role="error"] {
    color: #d64545;
    font-weight: 600;
}
QLabel[role="warning"] {
    color: #b8860b;
    font-weight: 600;
}
"""


def apply_app_style(app):
    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet(STYLESHEET)
    app.setFont(QFont(APP_FONT_FAMILY, BASE_FONT_SIZE))

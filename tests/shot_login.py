"""Ad-hoc screenshot generator for the redesigned login screen (design review only)."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

import database
from ui.theme import apply_app_style
from ui.pages.login_page import LoginScreen
from screenshot_helpers import save_screenshot

app = QApplication.instance() or QApplication([])
apply_app_style(app)

with tempfile.TemporaryDirectory() as tmp:
    db_path = Path(tmp) / "test_pos.db"
    conn = database.init_db(db_path)
    screen = LoginScreen(conn)
    out = save_screenshot(screen, sys.argv[1] if len(sys.argv) > 1 else "login.png")
    print("Saved:", out)
    conn.close()

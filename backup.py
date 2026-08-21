"""Automatic backup of the SQLite database file on app close.

Keeps only the 10 most recent backups; older ones are deleted.
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from database import DB_PATH

BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR / "backups"
MAX_BACKUPS = 10


def create_backup(db_path: Path | str = DB_PATH, backup_dir: Path | str = BACKUP_DIR) -> Path | None:
    """Copy the database file into backup_dir with a timestamped name.

    Returns the new backup's path, or None if there was no database file to back up.
    Also prunes backup_dir down to the MAX_BACKUPS most recent files.
    """
    db_path = Path(db_path)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup_path = backup_dir / f"backup_{timestamp}.db"

    # Avoid overwriting a backup made in the same minute
    counter = 1
    while backup_path.exists():
        backup_path = backup_dir / f"backup_{timestamp}_{counter}.db"
        counter += 1

    shutil.copy2(db_path, backup_path)
    prune_old_backups(backup_dir)
    return backup_path


def prune_old_backups(backup_dir: Path | str = BACKUP_DIR, keep: int = MAX_BACKUPS) -> None:
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return
    backups = sorted(backup_dir.glob("backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in backups[keep:]:
        stale.unlink()


if __name__ == "__main__":
    path = create_backup()
    print(f"Backup created: {path}" if path else "No database file found to back up.")

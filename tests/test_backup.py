"""Headless test for backup.py — run with `python tests/test_backup.py`."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database
import backup


def run():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "pos.db"
        backup_dir = tmp_path / "backups"

        conn = database.init_db(db_path)
        conn.close()

        # No DB present at a different path -> None
        assert backup.create_backup(tmp_path / "missing.db", backup_dir) is None
        print("OK: create_backup returns None when the DB file doesn't exist")

        b1 = backup.create_backup(db_path, backup_dir)
        assert b1 is not None and b1.exists()
        print("OK: first backup created:", b1.name)

        # Same-minute collision handling: force a second backup right away
        b2 = backup.create_backup(db_path, backup_dir)
        assert b2 is not None and b2 != b1 and b2.exists()
        print("OK: second backup in the same minute gets a distinct filename:", b2.name)

        files = list(backup_dir.glob("backup_*.db"))
        assert len(files) == 2
        print("OK: both backup files exist in the backup directory")

        # --- Pruning: create many backups by writing files directly with staggered mtimes ---
        for i in range(15):
            f = backup_dir / f"backup_synthetic_{i:02d}.db"
            f.write_bytes(b"x")
            # stagger mtimes so ordering is deterministic
            mtime = time.time() + i
            import os
            os.utime(f, (mtime, mtime))

        backup.prune_old_backups(backup_dir, keep=10)
        remaining = list(backup_dir.glob("backup_*.db"))
        assert len(remaining) == 10, f"expected exactly 10 backups kept, got {len(remaining)}"
        print("OK: prune_old_backups keeps exactly the 10 most recent files")

        # the most recent synthetic files (highest index / mtime) must survive
        remaining_names = {f.name for f in remaining}
        assert "backup_synthetic_14.db" in remaining_names
        assert "backup_synthetic_00.db" not in remaining_names
        print("OK: pruning correctly kept the newest files and removed the oldest")

    print("\nAll backup tests passed.")


if __name__ == "__main__":
    run()

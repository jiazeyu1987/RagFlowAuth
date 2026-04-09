from __future__ import annotations

import sqlite3
from pathlib import Path

from .common import ensure_dir


def sqlite_online_backup(src_db: Path, dest_db: Path) -> None:
    ensure_dir(dest_db.parent)

    src = sqlite3.connect(str(src_db), timeout=30.0)
    try:
        try:
            src.execute("PRAGMA busy_timeout = 5000")
        except sqlite3.OperationalError:
            pass

        dst = sqlite3.connect(str(dest_db), timeout=30.0)
        try:
            try:
                dst.execute("PRAGMA busy_timeout = 5000")
            except sqlite3.OperationalError:
                pass

            # Do not force a FULL checkpoint here. On a busy live DB it can block
            # long enough that the backup UI appears stuck at 10%.
            src.backup(dst, pages=1000, sleep=0.05)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()

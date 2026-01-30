from __future__ import annotations

import sqlite3
from pathlib import Path

from .common import ensure_dir


def sqlite_online_backup(src_db: Path, dest_db: Path) -> None:
    ensure_dir(dest_db.parent)

    # Remove existing backup file to ensure fresh copy
    if dest_db.exists():
        dest_db.unlink()

    src = sqlite3.connect(str(src_db))
    try:
        dst = sqlite3.connect(str(dest_db))
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()


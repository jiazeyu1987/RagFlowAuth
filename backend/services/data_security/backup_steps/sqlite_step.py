from __future__ import annotations

from pathlib import Path

from backend.app.core.paths import repo_root

from ..sqlite_backup import sqlite_online_backup
from .context import BackupContext


def backup_sqlite_db(ctx: BackupContext) -> None:
    ctx.raise_if_cancelled()
    if not ctx.pack_dir:
        raise RuntimeError("pack_dir_not_prepared")

    settings = ctx.settings
    pack_dir = ctx.pack_dir

    src_db = Path(settings.auth_db_path)
    if not src_db.is_absolute():
        src_db = repo_root() / src_db
    if not src_db.exists():
        raise RuntimeError(f"project_auth_db_not_found:{src_db}")

    ctx.update(message="backup_sqlite_started", progress=10)

    dest_db = pack_dir / "auth.db"
    sqlite_online_backup(src_db, dest_db)

    ctx.update(message="backup_sqlite_completed", progress=35)

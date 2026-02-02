from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path

from backend.app.core.paths import repo_root

from ..common import ensure_dir, timestamp
from ..sqlite_backup import sqlite_online_backup
from .context import BackupContext


def backup_sqlite_db(ctx: BackupContext) -> None:
    ctx.raise_if_cancelled()
    if not ctx.pack_dir:
        raise RuntimeError("pack_dir not prepared")

    settings = ctx.settings
    pack_dir = ctx.pack_dir

    src_db = Path(settings.auth_db_path)
    if not src_db.is_absolute():
        src_db = repo_root() / src_db
    if not src_db.exists():
        raise RuntimeError(f"找不到本项目数据库：{src_db}")

    ctx.update(message="备份本项目数据库", progress=10)

    dest_db = pack_dir / "auth.db"
    dest_db_norm = str(dest_db).replace("\\", "/")

    # NOTE: Writing sqlite online backup directly to a CIFS mount can hang (many small page writes).
    # If the pack dir is on `/mnt/replica`, stage the sqlite backup locally then copy to the share.
    if dest_db_norm.startswith("/mnt/replica/"):
        logger = logging.getLogger(__name__)

        tmp_root = Path("/tmp/ragflowauth_sqlite_backup")
        ensure_dir(tmp_root)
        tmp_db = tmp_root / f"auth_{ctx.job_id}_{timestamp()}.db"
        try:
            tmp_db.unlink()
        except Exception:
            pass

        ctx.update(message="备份数据库：先在本地生成 sqlite 备份（避免 CIFS 写入卡死）", progress=15)
        logger.info(f"[Backup] staging sqlite backup to local tmp: src={src_db} tmp={tmp_db} dest={dest_db}")
        sqlite_online_backup(src_db, tmp_db)
        ctx.raise_if_cancelled()

        dest_tmp = pack_dir / "auth.db.tmp"
        try:
            dest_tmp.unlink()
        except Exception:
            pass
        ctx.update(message="备份数据库：复制 sqlite 备份到 /mnt/replica", progress=25)
        shutil.copy2(tmp_db, dest_tmp)
        os.replace(dest_tmp, dest_db)

        try:
            size = dest_db.stat().st_size
        except Exception:
            size = -1
        if size <= 0:
            raise RuntimeError(f"sqlite backup write failed: {dest_db} (size={size})")

        try:
            tmp_db.unlink()
        except Exception:
            pass
    else:
        sqlite_online_backup(src_db, dest_db)

    ctx.update(message="本项目数据库已写入", progress=35)

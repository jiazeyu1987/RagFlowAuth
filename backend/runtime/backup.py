from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from backend.app.core.paths import repo_root
from backend.database.paths import resolve_auth_db_path


@dataclass(frozen=True)
class BackupConfig:
    enabled: bool
    method: str
    target_dir: Path
    retain_days: int


def default_backup_config_path() -> Path:
    return repo_root() / "backup_config.json"


def load_backup_config(path: str | Path | None = None) -> BackupConfig:
    config_path = Path(path) if path is not None else default_backup_config_path()
    data: dict = {}
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8") or "{}") or {}

    enabled = bool(data.get("enabled", True))
    method = str(data.get("method", "directory") or "directory").strip().lower()
    target_dir_raw = data.get("target_dir") or (repo_root() / "backups")
    target_dir = Path(str(target_dir_raw))
    retain_days = int(data.get("retain_days", 30) or 30)

    return BackupConfig(enabled=enabled, method=method, target_dir=target_dir, retain_days=retain_days)


def write_default_backup_config(path: str | Path | None = None) -> Path:
    config_path = Path(path) if path is not None else default_backup_config_path()
    if config_path.exists():
        return config_path
    sample = {
        "enabled": True,
        "method": "directory",
        "target_dir": r"\\192.168.1.100\backup\RagflowAuth",
        "retain_days": 30,
    }
    config_path.write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return config_path


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _sqlite_online_backup(src_db: Path, dest_db: Path) -> None:
    """
    Perform an online backup of sqlite DB (safe with WAL).
    """
    _ensure_dir(dest_db.parent)

    src = sqlite3.connect(str(src_db))
    try:
        # Ensure WAL contents are checkpointed into the main DB.
        try:
            src.execute("PRAGMA wal_checkpoint(FULL)")
        except sqlite3.OperationalError:
            pass

        dst = sqlite3.connect(str(dest_db))
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()


def _apply_retention(target_dir: Path, *, retain_days: int) -> int:
    if retain_days <= 0:
        return 0
    cutoff = time.time() - retain_days * 24 * 60 * 60
    deleted = 0
    for p in target_dir.glob("authdb_*.db"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
                deleted += 1
        except OSError:
            continue
    return deleted


def run_backup(*, config_path: str | Path | None = None, target_dir: str | Path | None = None) -> Path:
    cfg = load_backup_config(config_path)
    if not cfg.enabled:
        raise RuntimeError("备份已禁用（backup_config.json: enabled=false）")
    if cfg.method != "directory":
        raise RuntimeError(f"不支持的备份方式: {cfg.method}（目前仅支持 directory）")

    src_db = resolve_auth_db_path(None)
    if not src_db.exists():
        raise RuntimeError(f"未找到数据库文件: {src_db}")

    effective_target = Path(target_dir) if target_dir is not None else cfg.target_dir

    # Support UNC paths and local paths
    effective_target = Path(str(effective_target))
    _ensure_dir(effective_target)

    backup_name = f"authdb_{_timestamp()}.db"
    temp_dir = repo_root() / "data" / "backup_tmp"
    _ensure_dir(temp_dir)
    temp_backup = temp_dir / backup_name

    _sqlite_online_backup(src_db, temp_backup)

    final_backup = effective_target / backup_name
    try:
        os.replace(temp_backup, final_backup)
    except OSError:
        # Cross-device move or permission; fall back to copy then delete.
        final_backup.write_bytes(temp_backup.read_bytes())
        try:
            temp_backup.unlink()
        except OSError:
            pass

    deleted = _apply_retention(effective_target, retain_days=cfg.retain_days)
    if deleted:
        print(f"[OK] 已清理过期备份: {deleted} 个")

    return final_backup


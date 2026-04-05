from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class BackupCatalogEntry:
    path: Path
    label: str
    sort_key: tuple[int, str]  # (timestamp desc-ish via negative, fallback name)


_MIGRATION_PACK_RE = re.compile(r"^migration_pack_(\d{8})(?:_(\d{6}))?(?:_(\d{1,6}))?$")


def _try_parse_pack_datetime(folder_name: str) -> datetime | None:
    m = _MIGRATION_PACK_RE.match(folder_name)
    if not m:
        return None
    ymd = m.group(1)
    hms = m.group(2) or "000000"
    ms = m.group(3)
    try:
        dt = datetime.strptime(ymd + hms, "%Y%m%d%H%M%S")
    except Exception:
        return None
    if ms and ms.isdigit():
        # Keep milliseconds in label only; sort by seconds is good enough.
        pass
    return dt


def _format_label(folder_name: str) -> str:
    dt = _try_parse_pack_datetime(folder_name)
    if not dt:
        return folder_name
    base = dt.strftime("%Y-%m-%d %H:%M:%S")
    m = _MIGRATION_PACK_RE.match(folder_name)
    ms = m.group(3) if m else None
    if ms and ms.isdigit():
        return f"{base}.{ms}"
    return base


def list_local_backups(root_dir: Path) -> list[BackupCatalogEntry]:
    """
    List backup directories under `root_dir`.

    A "backup directory" is any folder that contains `auth.db` (required).
    """
    root = Path(root_dir)
    if not root.exists() or not root.is_dir():
        return []

    entries: list[BackupCatalogEntry] = []
    for p in root.iterdir():
        if not p.is_dir():
            continue
        if p.name.startswith("."):
            continue
        auth_db = p / "auth.db"
        if not auth_db.exists():
            continue
        label = _format_label(p.name)
        dt = _try_parse_pack_datetime(p.name)
        ts = int(dt.timestamp()) if dt else 0
        # Sort by newest first: use negative timestamp; tie-breaker by name.
        entries.append(BackupCatalogEntry(path=p, label=label, sort_key=(-ts, p.name)))

    entries.sort(key=lambda e: e.sort_key)
    return entries


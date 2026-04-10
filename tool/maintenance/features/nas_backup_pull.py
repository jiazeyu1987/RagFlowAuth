from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from tool.maintenance.core.constants import (
    DEFAULT_NAS_BACKUP_DIR,
    DEFAULT_NAS_PASSWORD,
    DEFAULT_NAS_SHARE_ROOT,
    DEFAULT_NAS_USERNAME,
)
from tool.maintenance.features.server_backup_pull import (
    ServerBackupDownloadResult,
    ServerBackupEntry,
    ServerBackupListResult,
    _parse_backup_entry,
)


def _normalize_output(stdout: str, stderr: str) -> str:
    return f"{stdout or ''}{stderr or ''}".strip()


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(os.path.normpath(str(right)))


def ensure_nas_backup_root_access(
    *,
    share_root: Path = DEFAULT_NAS_SHARE_ROOT,
    backup_root: Path = DEFAULT_NAS_BACKUP_DIR,
    username: str = DEFAULT_NAS_USERNAME,
    password: str = DEFAULT_NAS_PASSWORD,
    net_use_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[bool, str, str]:
    backup_root = Path(backup_root)
    share_root = Path(share_root)

    if backup_root.exists():
        if not backup_root.is_dir():
            return False, "", "nas_backup_root_not_directory"
        return True, "", "ok"

    argv = ["net", "use", str(share_root), password, f"/user:{username}", "/persistent:no"]
    try:
        completed = net_use_runner(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        return False, "", "net_use_not_found"

    output = _normalize_output(completed.stdout or "", completed.stderr or "")
    if completed.returncode != 0:
        return False, output, "nas_auth_failed"

    if not share_root.exists():
        return False, output, "nas_share_unreachable"
    if not share_root.is_dir():
        return False, output, "nas_share_not_directory"
    if not backup_root.exists():
        return False, output, "nas_backup_root_missing"
    if not backup_root.is_dir():
        return False, output, "nas_backup_root_not_directory"
    return True, output, "ok"


def list_nas_backup_dirs(
    *,
    backup_root: Path = DEFAULT_NAS_BACKUP_DIR,
    ensure_access: Callable[[], tuple[bool, str, str]] = ensure_nas_backup_root_access,
) -> ServerBackupListResult:
    ok, raw, message = ensure_access()
    if not ok:
        return ServerBackupListResult(ok=False, backups=[], raw=raw, message=message)

    root = Path(backup_root)
    try:
        names = [entry.name for entry in root.iterdir() if entry.is_dir()]
    except OSError as exc:
        return ServerBackupListResult(ok=False, backups=[], raw=str(exc), message="list_failed")

    parsed: list[ServerBackupEntry] = []
    for name in names:
        entry = _parse_backup_entry(name)
        if entry is not None:
            parsed.append(entry)

    parsed.sort(key=lambda item: item.name, reverse=True)
    if not parsed:
        return ServerBackupListResult(ok=False, backups=[], raw="", message="no_backups_found")

    return ServerBackupListResult(ok=True, backups=parsed, raw=raw, message="ok")


def download_nas_backup_dir(
    *,
    name: str,
    destination_root: str | Path,
    backup_root: Path = DEFAULT_NAS_BACKUP_DIR,
    ensure_access: Callable[[], tuple[bool, str, str]] = ensure_nas_backup_root_access,
    copytree_func: Callable[..., str] = shutil.copytree,
) -> ServerBackupDownloadResult:
    name = (name or "").strip()
    if _parse_backup_entry(name) is None:
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination="",
            raw="",
            message="invalid_name",
        )

    local_root = Path(destination_root).expanduser()
    if local_root.exists() and not local_root.is_dir():
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination=str(local_root),
            raw="",
            message="destination_root_not_directory",
        )

    try:
        local_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination=str(local_root),
            raw=str(exc),
            message="destination_root_create_failed",
        )

    ok, raw, message = ensure_access()
    if not ok:
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination=str(local_root / name),
            raw=raw,
            message=message,
        )

    root = Path(backup_root)
    source_dir = root / name
    local_target = local_root / name

    if _same_path(source_dir, local_target):
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination=str(local_target),
            raw="",
            message="destination_same_as_source",
        )

    if local_target.exists():
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination=str(local_target),
            raw="",
            message="destination_exists",
        )

    if not source_dir.exists() or not source_dir.is_dir():
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination=str(local_target),
            raw="",
            message="remote_backup_missing",
        )

    try:
        copytree_func(str(source_dir), str(local_target))
    except OSError as exc:
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination=str(local_target),
            raw=str(exc),
            message="local_copy_failed",
        )

    return ServerBackupDownloadResult(
        ok=True,
        name=name,
        destination=str(local_target),
        raw=raw,
        message="downloaded",
    )

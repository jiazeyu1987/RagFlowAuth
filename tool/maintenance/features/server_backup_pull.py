from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from tool.maintenance.core.constants import DEFAULT_LOCAL_BACKUP_DIR
from tool.maintenance.core.logging_setup import log_to_file
from tool.maintenance.core.ssh_executor import SSHExecutor, build_scp_argv
from tool.maintenance.core.tempdir import cleanup_dir, make_temp_dir

REMOTE_BACKUP_ROOT = "/opt/ragflowauth/backups"
DEFAULT_LOCAL_SAVE_DIR = Path(DEFAULT_LOCAL_BACKUP_DIR)

_BACKUP_PREFIX_LABELS = {
    "migration_pack": "增量备份",
    "full_backup_pack": "全量备份",
}


@dataclass(frozen=True)
class ServerBackupEntry:
    name: str
    display_name: str
    backup_type: str
    created_at: str


@dataclass(frozen=True)
class ServerBackupListResult:
    ok: bool
    backups: list[ServerBackupEntry]
    raw: str
    message: str


@dataclass(frozen=True)
class ServerBackupDownloadResult:
    ok: bool
    name: str
    destination: str
    raw: str
    message: str


def _parse_backup_entry(name: str) -> ServerBackupEntry | None:
    name = (name or "").strip()
    for prefix, type_label in _BACKUP_PREFIX_LABELS.items():
        if not name.startswith(f"{prefix}_"):
            continue

        tail = name[len(prefix) + 1 :]
        parts = tail.split("_")
        if len(parts) < 2:
            return None

        date_part = parts[0]
        time_part = parts[1]
        if len(date_part) != 8 or len(time_part) != 6 or not date_part.isdigit() or not time_part.isdigit():
            return None

        try:
            created = datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M%S")
        except ValueError:
            return None

        display_name = f"{created:%Y-%m-%d %H:%M:%S} ({type_label})"
        return ServerBackupEntry(
            name=name,
            display_name=display_name,
            backup_type=type_label,
            created_at=f"{created:%Y-%m-%d %H:%M:%S}",
        )

    return None


def _is_valid_backup_name(name: str) -> bool:
    return _parse_backup_entry(name) is not None


def _strip_noise(output: str) -> str:
    return SSHExecutor._strip_known_noise(output).strip()


def list_server_backup_dirs(*, server_ip: str, server_user: str = "root") -> ServerBackupListResult:
    if not shutil.which("ssh"):
        return ServerBackupListResult(ok=False, backups=[], raw="", message="ssh_not_found")

    ssh = SSHExecutor(server_ip, server_user)
    command = (
        f"cd {REMOTE_BACKUP_ROOT} 2>/dev/null && "
        "for d in migration_pack_* full_backup_pack_*; do "
        "[ -d \"$d\" ] && printf '%s\\n' \"$d\"; "
        "done | sort -r"
    )

    try:
        ok, out = ssh.execute(command, timeout_seconds=60)
    except FileNotFoundError:
        return ServerBackupListResult(ok=False, backups=[], raw="", message="ssh_not_found")

    raw = (out or "").strip()
    if not ok:
        return ServerBackupListResult(ok=False, backups=[], raw=raw, message="list_failed")

    parsed: list[ServerBackupEntry] = []
    for line in raw.splitlines():
        entry = _parse_backup_entry(line)
        if entry is not None:
            parsed.append(entry)

    parsed.sort(key=lambda item: item.name, reverse=True)
    if not parsed:
        return ServerBackupListResult(ok=False, backups=[], raw=raw, message="no_backups_found")

    return ServerBackupListResult(ok=True, backups=parsed, raw=raw, message="ok")


def download_server_backup_dir(
    *,
    server_ip: str,
    name: str,
    destination_root: str | Path,
    server_user: str = "root",
    scp_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ServerBackupDownloadResult:
    name = (name or "").strip()
    if not _is_valid_backup_name(name):
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination="",
            raw="",
            message="invalid_name",
        )

    if not shutil.which("ssh"):
        return ServerBackupDownloadResult(ok=False, name=name, destination="", raw="", message="ssh_not_found")
    if not shutil.which("scp"):
        return ServerBackupDownloadResult(ok=False, name=name, destination="", raw="", message="scp_not_found")

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

    local_target = local_root / name
    if local_target.exists():
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination=str(local_target),
            raw="",
            message="destination_exists",
        )

    ssh = SSHExecutor(server_ip, server_user)
    exists_command = (
        f"cd {REMOTE_BACKUP_ROOT} 2>/dev/null && "
        f"test -d '{name}' && printf 'READY\\n'"
    )
    try:
        ok, out = ssh.execute(exists_command, timeout_seconds=60)
    except FileNotFoundError:
        return ServerBackupDownloadResult(ok=False, name=name, destination="", raw="", message="ssh_not_found")

    if not ok or (out or "").strip() != "READY":
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination=str(local_target),
            raw=(out or "").strip(),
            message="remote_backup_missing",
        )

    temp_root = make_temp_dir(prefix="ragflowauth_pull_backup")
    source = f"{server_user}@{server_ip}:{REMOTE_BACKUP_ROOT}/{name}"
    argv = build_scp_argv("-q", "-r", source, str(temp_root))

    log_to_file(f"[ServerBackupPull] download start: {source} -> {local_root}")

    try:
        completed = scp_runner(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = _strip_noise(f"{completed.stdout or ''}{completed.stderr or ''}")
        if completed.returncode != 0:
            return ServerBackupDownloadResult(
                ok=False,
                name=name,
                destination=str(local_target),
                raw=output,
                message="scp_failed",
            )

        downloaded_dir = temp_root / name
        if not downloaded_dir.is_dir():
            return ServerBackupDownloadResult(
                ok=False,
                name=name,
                destination=str(local_target),
                raw=output,
                message="downloaded_dir_missing",
            )

        shutil.move(str(downloaded_dir), str(local_root))
        return ServerBackupDownloadResult(
            ok=True,
            name=name,
            destination=str(local_target),
            raw=output,
            message="downloaded",
        )
    except OSError as exc:
        return ServerBackupDownloadResult(
            ok=False,
            name=name,
            destination=str(local_target),
            raw=str(exc),
            message="local_move_failed",
        )
    finally:
        cleanup_dir(temp_root)

from __future__ import annotations

import re
from dataclasses import dataclass

from tool.maintenance.core.ssh_executor import SSHExecutor

REPLICA_ROOT = "/opt/ragflowauth/data/backups"

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class ReplicaBackupsListResult:
    ok: bool
    names: list[str]
    raw: str


@dataclass(frozen=True)
class ReplicaBackupDeleteResult:
    ok: bool
    name: str
    raw: str
    message: str


def list_replica_backup_dirs(*, server_ip: str, server_user: str = "root") -> ReplicaBackupsListResult:
    ssh = SSHExecutor(server_ip, server_user)
    cmd = (
        f"cd {REPLICA_ROOT} 2>/dev/null && "
        "ls -1dt */ 2>/dev/null | sed 's:/*$::' || true"
    )
    ok, out = ssh.execute(cmd, timeout_seconds=60)
    raw = (out or "").strip()
    names = [line.strip().rstrip("/") for line in raw.splitlines() if line.strip()]
    return ReplicaBackupsListResult(ok=bool(ok), names=names, raw=raw)


def delete_replica_backup_dir(
    *,
    server_ip: str,
    name: str,
    server_user: str = "root",
) -> ReplicaBackupDeleteResult:
    name = (name or "").strip()
    if not name or "/" in name or "\\" in name or ".." in name or not _SAFE_NAME_RE.match(name):
        return ReplicaBackupDeleteResult(ok=False, name=name, raw="", message="invalid_name")

    ssh = SSHExecutor(server_ip, server_user)
    # Extra safety: ensure target path is exactly under REPLICA_ROOT and is a directory.
    cmd = (
        f"set -e; "
        f"cd {REPLICA_ROOT}; "
        f"test -d '{name}' || (echo 'NOT_DIR' && exit 2); "
        f"rm -rf -- '{name}'; "
        f"echo 'DELETED'"
    )
    ok, out = ssh.execute(cmd, timeout_seconds=300)
    raw = (out or "").strip()
    if ok and "DELETED" in raw:
        return ReplicaBackupDeleteResult(ok=True, name=name, raw=raw, message="deleted")
    return ReplicaBackupDeleteResult(ok=False, name=name, raw=raw, message="delete_failed")

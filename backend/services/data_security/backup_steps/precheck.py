from __future__ import annotations

from pathlib import Path

from backend.app.core.managed_paths import managed_data_root
from backend.app.core.paths import repo_root
from backend.services.mount_utils import is_cifs_mounted

from ..common import ensure_dir, timestamp
from ..docker_utils import docker_ok
from ..models import STANDARD_NAS_MOUNT_ROOT, is_standard_nas_path
from .context import BackupContext


def _local_staging_root_for_target(local_target: str) -> Path:
    target = str(local_target or "").strip()
    if is_standard_nas_path(target):
        return managed_data_root() / "backups" / "_staging_local"
    return Path(target) / "_staging"


def backup_precheck_and_prepare(ctx: BackupContext) -> None:
    ctx.raise_if_cancelled()
    settings = ctx.settings

    local_target = str(settings.local_backup_target_path() or "").strip()
    if not local_target:
        raise RuntimeError("local_backup_target_not_configured")
    if is_standard_nas_path(local_target) and not is_cifs_mounted(STANDARD_NAS_MOUNT_ROOT):
        raise RuntimeError(f"local_backup_target_mount_not_cifs:{STANDARD_NAS_MOUNT_ROOT}")

    ok, why = docker_ok()
    if not ok:
        raise RuntimeError(f"docker_unavailable:{why}")

    local_root = Path(local_target)
    staging_root = _local_staging_root_for_target(local_target) / f"job_{ctx.job_id}"
    ensure_dir(staging_root)

    try:
        probe = staging_root / f".write_probe_{ctx.job_id}_{timestamp()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as exc:
        raise RuntimeError(f"local_backup_target_not_writable:{local_root} err={exc}") from exc

    ctx.target = local_target
    ctx.local_backup_root = local_root
    ctx.staging_root = staging_root
    ctx.windows_target = settings.windows_target_path()

    ctx.raise_if_cancelled()
    pack_dir = staging_root / f"migration_pack_{timestamp()}"
    ensure_dir(pack_dir)
    ctx.pack_dir = pack_dir
    ctx.update(message="backup_staging_prepared", progress=3)

    src_db = Path(settings.auth_db_path)
    if not src_db.is_absolute():
        src_db = repo_root() / src_db
    if not src_db.exists():
        raise RuntimeError(f"project_auth_db_not_found:{src_db}")

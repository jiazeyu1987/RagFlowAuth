from __future__ import annotations

from pathlib import Path

from backend.app.core.paths import repo_root

from ..common import ensure_dir, timestamp
from ..docker_utils import docker_ok
from .context import BackupContext


def backup_precheck_and_prepare(ctx: BackupContext) -> None:
    ctx.raise_if_cancelled()
    settings = ctx.settings

    local_target = str(settings.local_backup_target_path() or "").strip()
    if not local_target:
        raise RuntimeError("local_backup_target_not_configured")

    ok, why = docker_ok()
    if not ok:
        raise RuntimeError(f"docker_unavailable:{why}")

    local_root = Path(local_target)
    staging_root = local_root / "_staging" / f"job_{ctx.job_id}"
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

from __future__ import annotations

import logging
from pathlib import Path

from backend.app.core.paths import repo_root

from ..common import ensure_dir, timestamp
from ..docker_utils import docker_ok
from .context import BackupContext


def _norm_path(s: str) -> str:
    return str(s).replace("\\", "/")


def _mount_fstype(mountpoint: str) -> str | None:
    """
    Best-effort: detect filesystem type for a mountpoint inside the backend container.

    Used to ensure `/mnt/replica` is a real CIFS mount when target is under that path.
    """
    mp = _norm_path(mountpoint).rstrip("/") or "/"
    try:
        data = Path("/proc/mounts").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    best: tuple[str, str] | None = None  # (mnt, fstype)
    for line in data.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mnt = parts[1]
        fstype = parts[2]
        if mnt == mp or mp.startswith(mnt.rstrip("/") + "/"):
            if best is None or len(mnt) > len(best[0]):
                best = (mnt, fstype)
    return best[1] if best else None


def backup_precheck_and_prepare(ctx: BackupContext) -> None:
    ctx.raise_if_cancelled()
    settings = ctx.settings
    target = settings.target_path()
    if not target:
        raise RuntimeError("未配置备份目标（请设置目标电脑IP/共享目录，或选择本地目录）")

    ok, why = docker_ok()
    if not ok:
        raise RuntimeError(f"Docker 不可用：{why}")

    ctx.target = target

    target_norm = _norm_path(target)
    if target_norm.startswith("/mnt/replica/"):
        logger = logging.getLogger(__name__)
        ctx.update(message="Precheck: 验证 /mnt/replica 为 CIFS 且可写", progress=2)

        fstype = _mount_fstype("/mnt/replica")
        logger.info(f"[Backup] /mnt/replica fstype={fstype!r} target={target_norm}")
        if fstype != "cifs":
            raise RuntimeError(
                "备份目标在 /mnt/replica 下，但 /mnt/replica 不是 CIFS 挂载（可能没挂载 Windows 共享，写入会落到本地磁盘）。"
                f"fstype={fstype!r}"
            )

        try:
            ensure_dir(Path(target))
            probe = Path(target) / f".write_probe_{ctx.job_id}_{timestamp()}"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except Exception as e:
            raise RuntimeError(f"备份目标不可写：{target_norm} err={e}")

    ctx.raise_if_cancelled()
    pack_dir = Path(target) / f"migration_pack_{timestamp()}"
    ensure_dir(pack_dir)
    ctx.pack_dir = pack_dir
    ctx.update(message="创建迁移包目录", progress=3, output_dir=str(pack_dir))

    # Sanity check: auth db path exists (resolve relative to repo root like legacy behavior)
    src_db = Path(settings.auth_db_path)
    if not src_db.is_absolute():
        src_db = repo_root() / src_db
    if not src_db.exists():
        raise RuntimeError(f"找不到本项目数据库：{src_db}")

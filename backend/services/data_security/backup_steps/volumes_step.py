from __future__ import annotations

from pathlib import Path

from backend.app.core.paths import repo_root

from ..common import ensure_dir
from ..docker_utils import (
    docker_compose_start,
    docker_compose_stop,
    list_docker_volumes_by_prefix,
    read_compose_project_name,
    docker_tar_volume,
)
from .context import BackupContext, BackupCancelledError


def backup_ragflow_volumes(ctx: BackupContext) -> None:
    ctx.raise_if_cancelled()
    if not ctx.pack_dir:
        raise RuntimeError("pack_dir not prepared")

    settings = ctx.settings

    compose_path = (settings.ragflow_compose_path or "").strip()
    if not compose_path:
        raise RuntimeError("未设置 RAGFlow docker-compose.yml 路径（请在“数据安全”里选择）")
    compose_file = Path(compose_path)
    if not compose_file.is_absolute():
        compose_file = repo_root() / compose_file
    if not compose_file.exists():
        raise RuntimeError(f"找不到 RAGFlow docker-compose.yml：{compose_file}")

    ctx.compose_file = compose_file
    project = read_compose_project_name(compose_file)
    ctx.ragflow_project = project
    prefix = f"{project}_"

    if settings.ragflow_stop_services:
        ctx.update(message="停止 RAGFlow 服务（可选）", progress=38)
        docker_compose_stop(compose_file)

    try:
        ctx.raise_if_cancelled()
        ctx.update(message="枚举 RAGFlow volumes", progress=42)
        vols = list_docker_volumes_by_prefix(prefix)
        if not vols:
            raise RuntimeError(f"未找到任何 RAGFlow volumes（prefix={prefix}）")

        ensure_dir(ctx.pack_dir / "volumes")
        step = max(1, int(40 / max(1, len(vols))))
        prog = 45
        for v in vols:
            ctx.raise_if_cancelled()
            ctx.update(message=f"备份 volume: {v}", progress=min(90, prog))
            dest_tar = ctx.pack_dir / "volumes" / f"{v}.tar.gz"

            def _hb_volume(*, _dest: Path = dest_tar, _v: str = v, _p: int = min(90, prog)) -> None:
                try:
                    size = _dest.stat().st_size
                except Exception:
                    size = 0
                mb = size / 1024 / 1024
                try:
                    ctx.raise_if_cancelled()
                    ctx.update(message=f"备份 volume: {_v}（写入中 {mb:.1f} MB）", progress=_p)
                except Exception:
                    pass

            try:
                docker_tar_volume(
                    v,
                    dest_tar,
                    heartbeat=_hb_volume,
                    cancel_check=lambda: ctx.store.is_cancel_requested(ctx.job_id),
                )
            except RuntimeError as e:
                if "[cancelled]" in str(e):
                    raise BackupCancelledError("backup_cancel_requested") from e
                raise
            prog += step
    finally:
        if settings.ragflow_stop_services:
            try:
                ctx.update(message="启动 RAGFlow 服务（可选）", progress=96)
                docker_compose_start(compose_file)
            except Exception:
                pass

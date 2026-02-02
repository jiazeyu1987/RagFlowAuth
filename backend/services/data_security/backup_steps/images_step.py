from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from ..common import run_cmd
from ..docker_utils import (
    docker_save_images,
    list_compose_images,
    list_running_container_images,
)
from .context import BackupContext, BackupCancelledError


def backup_docker_images(ctx: BackupContext, *, progress_base: int = 92) -> None:
    """
    Optional images backup.

    Mirrors the legacy behavior in backup_service.py, including:
    - compose images list with docker ps fallback
    - disk space precheck (best-effort)
    - heartbeat progress updates
    - verify images.tar created on container-visible filesystem
    """
    if not ctx.pack_dir:
        raise RuntimeError("pack_dir not prepared")
    if not ctx.compose_file:
        raise RuntimeError("compose_file not prepared")
    if not ctx.include_images:
        ctx.update(message="跳过Docker镜像备份", progress=progress_base)
        return
    ctx.raise_if_cancelled()

    compose_file = ctx.compose_file
    project = ctx.ragflow_project or ""
    logger = logging.getLogger(__name__)

    ctx.update(message="开始备份Docker镜像...", progress=progress_base)
    images, err = list_compose_images(compose_file)
    if err or not images:
        fallback = list_running_container_images(name_prefix=project)
        if fallback:
            images = sorted(set(images or []) | set(fallback))
            ctx.update(message=f"镜像列表fallback(docker ps)：共{len(images)}个", progress=progress_base + 1)
        else:
            if err:
                ctx.update(message=f"跳过镜像备份：{err}", progress=progress_base + 3)
            else:
                ctx.update(message="跳过镜像备份：未找到可备份的镜像", progress=progress_base + 3)
            images = []

    if not images:
        return

    images_dest = ctx.pack_dir / "images.tar"
    logger.info(f"Saving {len(images)} images to {images_dest}")
    ctx.update(message=f"正在备份{len(images)}个Docker镜像...", progress=progress_base + 1)

    try:
        try:
            code_sz, out_sz = run_cmd(["docker", "image", "inspect", "--format", "{{.Size}}", *images])
            sizes: list[int] = []
            if code_sz == 0 and out_sz:
                for line in out_sz.splitlines():
                    line = (line or "").strip()
                    if not line:
                        continue
                    try:
                        sizes.append(int(line))
                    except Exception:
                        continue
            approx_need = sum(sizes) if sizes else 0
            free_bytes = int(shutil.disk_usage(str(ctx.pack_dir)).free)
            if approx_need > 0 and approx_need + 512 * 1024 * 1024 > free_bytes:
                msg = (
                    "镜像备份已跳过：服务器磁盘空间不足"
                    f"（free≈{free_bytes/1024/1024/1024:.1f}GB, need≈{approx_need/1024/1024/1024:.1f}GB）"
                )
                logger.error(msg)
                ctx.update(message=msg, progress=progress_base + 3)
                images = []
        except Exception as e:
            logger.warning(f"Images disk precheck failed: {e}")

        if not images:
            ok_save, err2 = False, None
        else:

            def _hb_images(*, _dest: Path = images_dest, _p: int = progress_base + 3) -> None:
                try:
                    size = _dest.stat().st_size
                except Exception:
                    size = 0
                mb = size / 1024 / 1024
                try:
                    ctx.raise_if_cancelled()
                    ctx.update(message=f"正在备份Docker镜像…（已写入 {mb:.1f} MB）", progress=_p)
                except Exception:
                    pass

            ok_save, err2 = docker_save_images(
                images,
                images_dest,
                heartbeat=_hb_images,
                cancel_check=lambda: ctx.store.is_cancel_requested(ctx.job_id),
            )

        logger.info(f"docker_save_images result: ok={ok_save}, err={err2}")
        if not ok_save and err2:
            if "[cancelled]" in str(err2):
                raise BackupCancelledError("backup_cancel_requested")
            ctx.update(message=f"镜像备份失败（已跳过）：{err2}", progress=progress_base + 3)
            return

        images_dest_str = str(images_dest).replace("\\", "/")
        if os.path.exists(images_dest_str):
            size = os.path.getsize(images_dest_str)
            logger.info(f"Images file created: {images_dest_str} ({size/1024/1024:.2f} MB)")
            ctx.update(message=f"镜像已备份（{len(images)}）", progress=progress_base + 3)
        else:
            logger.error(f"Images file NOT created at {images_dest_str}")
            ctx.update(message=f"镜像备份失败：文件未创建({images_dest_str})", progress=progress_base + 3)
    except Exception as e:
        logger.error(f"Exception during image backup: {e}", exc_info=True)
        ctx.update(message=f"镜像备份异常：{str(e)}", progress=progress_base + 3)

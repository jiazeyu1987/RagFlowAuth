from __future__ import annotations

import json
import time
from pathlib import Path

from backend.app.core.paths import repo_root
from backend.services.data_security_store import DataSecurityStore

from .common import ensure_dir, timestamp, run_cmd
from .docker_utils import (
    docker_ok,
    docker_compose_start,
    docker_compose_stop,
    docker_save_images,
    docker_tar_volume,
    list_compose_images,
    list_running_container_images,
    list_docker_volumes_by_prefix,
    read_compose_project_name,
)
from .sqlite_backup import sqlite_online_backup


# Keep a compatibility helper for older modules that import `_run` from `data_security_backup`.
def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    return run_cmd(cmd, cwd=cwd)


class DataSecurityBackupService:
    def __init__(self, store: DataSecurityStore) -> None:
        self.store = store

    def run_job(self, job_id: int, *, include_images: bool | None = None) -> None:
        job_kind: str | None = None
        try:
            job_kind = self.store.get_job(job_id).kind
        except Exception:
            job_kind = None

        settings = self.store.get_settings()
        target = settings.target_path()
        if not target:
            raise RuntimeError("未配置备份目标（请设置目标电脑IP/共享目录，或选择本地目录）")

        ok, why = docker_ok()
        if not ok:
            raise RuntimeError(f"Docker 不可用：{why}")

        if include_images is None:
            include_images = bool(getattr(settings, "full_backup_include_images", 1))

        now_ms = int(time.time() * 1000)
        self.store.update_job(job_id, status="running", progress=1, message="开始备份", started_at_ms=now_ms)

        def _norm_path(s: str) -> str:
            return str(s).replace("\\", "/")

        def _mount_fstype(mountpoint: str) -> str | None:
            """
            Best-effort: detect filesystem type for a mountpoint inside the backend container.

            We use this to ensure `/mnt/replica` is a real CIFS mount. If it's not mounted, writes to
            `/mnt/replica/...` may silently go to local disk and later cause space issues or missing backups.
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

        target_norm = _norm_path(target)
        if target_norm.startswith("/mnt/replica/"):
            import logging

            logger = logging.getLogger(__name__)
            self.store.update_job(job_id, message="Precheck: 验证 /mnt/replica 为 CIFS 且可写", progress=2)

            fstype = _mount_fstype("/mnt/replica")
            logger.info(f"[Backup] /mnt/replica fstype={fstype!r} target={target_norm}")
            if fstype != "cifs":
                raise RuntimeError(
                    "备份目标在 /mnt/replica 下，但 /mnt/replica 不是 CIFS 挂载（可能没挂载 Windows 共享，写入会落到本地磁盘）。"
                    f"fstype={fstype!r}"
                )

            # Quick write test (fail fast if share is read-only or disconnected).
            try:
                ensure_dir(Path(target))
                probe = Path(target) / f".write_probe_{job_id}_{timestamp()}"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink()
            except Exception as e:
                raise RuntimeError(f"备份目标不可写：{target_norm} err={e}")

        pack_dir = Path(target) / f"migration_pack_{timestamp()}"
        ensure_dir(pack_dir)
        self.store.update_job(job_id, output_dir=str(pack_dir), message="创建迁移包目录", progress=3)

        # 1) auth.db
        src_db = Path(settings.auth_db_path)
        if not src_db.is_absolute():
            src_db = repo_root() / src_db
        if not src_db.exists():
            raise RuntimeError(f"找不到本项目数据库：{src_db}")
        self.store.update_job(job_id, message="备份本项目数据库", progress=10)
        # NOTE: Writing sqlite online backup directly to a CIFS mount can hang (many small page writes).
        # If the pack dir is on `/mnt/replica`, stage the sqlite backup locally then copy to the share.
        dest_db = pack_dir / "auth.db"
        dest_db_norm = str(dest_db).replace("\\", "/")
        if dest_db_norm.startswith("/mnt/replica/"):
            import logging
            import os
            import shutil

            logger = logging.getLogger(__name__)

            tmp_root = Path("/tmp/ragflowauth_sqlite_backup")
            ensure_dir(tmp_root)
            tmp_db = tmp_root / f"auth_{job_id}_{timestamp()}.db"
            try:
                tmp_db.unlink()
            except Exception:
                pass

            self.store.update_job(job_id, message="备份数据库：先在本地生成 sqlite 备份（避免 CIFS 写入卡死）", progress=15)
            logger.info(f"[Backup] staging sqlite backup to local tmp: src={src_db} tmp={tmp_db} dest={dest_db}")
            sqlite_online_backup(src_db, tmp_db)

            # Copy into the CIFS-backed pack dir, using an atomic replace on the destination filesystem.
            dest_tmp = pack_dir / "auth.db.tmp"
            try:
                dest_tmp.unlink()
            except Exception:
                pass
            self.store.update_job(job_id, message="备份数据库：复制 sqlite 备份到 /mnt/replica", progress=25)
            shutil.copy2(tmp_db, dest_tmp)
            os.replace(dest_tmp, dest_db)

            try:
                size = dest_db.stat().st_size
            except Exception:
                size = -1
            if size <= 0:
                raise RuntimeError(f"sqlite backup write failed: {dest_db} (size={size})")

            try:
                tmp_db.unlink()
            except Exception:
                pass
        else:
            sqlite_online_backup(src_db, dest_db)
        self.store.update_job(job_id, message="本项目数据库已写入", progress=35)

        # 2) ragflow volumes
        compose_path = (settings.ragflow_compose_path or "").strip()
        if not compose_path:
            raise RuntimeError("未设置 RAGFlow docker-compose.yml 路径（请在“数据安全”里选择）")
        compose_file = Path(compose_path)
        if not compose_file.is_absolute():
            compose_file = repo_root() / compose_file
        if not compose_file.exists():
            raise RuntimeError(f"找不到 RAGFlow docker-compose.yml：{compose_file}")

        project = read_compose_project_name(compose_file)
        prefix = f"{project}_"

        # Optional: stop services for consistent backups
        if settings.ragflow_stop_services:
            self.store.update_job(job_id, message="停止 RAGFlow 服务（可选）", progress=38)
            docker_compose_stop(compose_file)

        try:
            self.store.update_job(job_id, message="枚举 RAGFlow volumes", progress=42)
            vols = list_docker_volumes_by_prefix(prefix)
            if not vols:
                raise RuntimeError(f"未找到任何 RAGFlow volumes（prefix={prefix}）")

            ensure_dir(pack_dir / "volumes")
            step = max(1, int(40 / max(1, len(vols))))
            prog = 45
            for v in vols:
                self.store.update_job(job_id, message=f"备份 volume: {v}", progress=min(90, prog))
                dest_tar = pack_dir / "volumes" / f"{v}.tar.gz"

                def _hb_volume(*, _dest: Path = dest_tar, _v: str = v, _p: int = min(90, prog)) -> None:
                    try:
                        size = _dest.stat().st_size
                    except Exception:
                        size = 0
                    mb = size / 1024 / 1024
                    try:
                        self.store.update_job(job_id, message=f"备份 volume: {_v}（写入中 {mb:.1f} MB）", progress=_p)
                    except Exception:
                        pass

                docker_tar_volume(v, dest_tar, heartbeat=_hb_volume)
                prog += step

            # 3) images (optional)
            if include_images:
                self.store.update_job(job_id, message=f"开始备份Docker镜像...", progress=min(92, prog))
                images, err = list_compose_images(compose_file)
                if err or not images:
                    # Fallback: derive image list from existing compose containers.
                    # This avoids failures when `docker compose config --images` can't be resolved
                    # (e.g. missing env vars) but the stack is already running.
                    # NOTE: compose project containers are usually named like `{project}-service-1` (hyphen),
                    # while volumes are usually `{project}_xxx` (underscore). Use the bare project name as
                    # prefix; the helper handles common delimiters.
                    fallback = list_running_container_images(name_prefix=project)
                    if fallback:
                        images = sorted(set(images or []) | set(fallback))
                        self.store.update_job(
                            job_id,
                            message=f"镜像列表fallback(docker ps)：共{len(images)}个",
                            progress=min(93, prog),
                        )
                    else:
                        if err:
                            self.store.update_job(job_id, message=f"跳过镜像备份：{err}", progress=min(95, prog))
                        else:
                            self.store.update_job(job_id, message="跳过镜像备份：未找到可备份的镜像", progress=min(95, prog))
                        images = []

                if images:
                    import logging
                    logger = logging.getLogger(__name__)
                    images_dest = pack_dir / "images.tar"
                    logger.info(f"Saving {len(images)} images to {images_dest}")
                    self.store.update_job(job_id, message=f"正在备份{len(images)}个Docker镜像...", progress=min(93, prog))
                    try:
                        # Precheck disk space: images tar can be huge, and writing it under the local backup dir
                        # requires enough free space on the underlying filesystem.
                        try:
                            import shutil

                            code_sz, out_sz = run_cmd(["docker", "image", "inspect", "--format", "{{.Size}}", *images])
                            sizes = []
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
                            free_bytes = int(shutil.disk_usage(str(pack_dir)).free)

                            # If we can estimate size and it's close to (or larger than) free space, skip early with a clear message.
                            # Keep a 512MB safety margin to avoid filling the disk.
                            if approx_need > 0 and approx_need + 512 * 1024 * 1024 > free_bytes:
                                msg = (
                                    "镜像备份已跳过：服务器磁盘空间不足"
                                    f"（free≈{free_bytes/1024/1024/1024:.1f}GB, need≈{approx_need/1024/1024/1024:.1f}GB）"
                                )
                                logger.error(msg)
                                self.store.update_job(job_id, message=msg, progress=min(95, prog))
                                images = []
                        except Exception as e:
                            # Best-effort: do not block image backup on precheck errors.
                            logger.warning(f"Images disk precheck failed: {e}")

                        if not images:
                            # Precheck decided to skip (message already written).
                            ok_save, err2 = False, None
                        else:

                            def _hb_images(*, _dest: Path = images_dest, _p: int = min(95, prog)) -> None:
                                try:
                                    size = _dest.stat().st_size
                                except Exception:
                                    size = 0
                                mb = size / 1024 / 1024
                                try:
                                    self.store.update_job(job_id, message=f"正在备份Docker镜像…（已写入 {mb:.1f} MB）", progress=_p)
                                except Exception:
                                    pass

                            ok_save, err2 = docker_save_images(images, images_dest, heartbeat=_hb_images)
                        logger.info(f"docker_save_images result: ok={ok_save}, err={err2}")
                        if not ok_save and err2:
                            self.store.update_job(job_id, message=f"镜像备份失败（已跳过）：{err2}", progress=min(95, prog))
                        else:
                            # Verify file was created (container-visible path).
                            # The backup service runs inside the backend container, so `docker save -o <path>`
                            # writes to the container filesystem (typically under a bind mount like `/app/data/backups`).
                            import os

                            images_dest_str = str(images_dest).replace("\\", "/")
                            if os.path.exists(images_dest_str):
                                size = os.path.getsize(images_dest_str)
                                logger.info(f"Images file created: {images_dest_str} ({size/1024/1024:.2f} MB)")
                                self.store.update_job(job_id, message=f"镜像已备份（{len(images)}）", progress=min(95, prog))
                            else:
                                logger.error(f"Images file NOT created at {images_dest_str}")
                                self.store.update_job(job_id, message=f"镜像备份失败：文件未创建({images_dest_str})", progress=min(95, prog))
                    except Exception as e:
                        logger.error(f"Exception during image backup: {e}", exc_info=True)
                        self.store.update_job(job_id, message=f"镜像备份异常：{str(e)}", progress=min(95, prog))
            else:
                self.store.update_job(job_id, message="跳过Docker镜像备份", progress=min(95, prog))

            # 4) config snapshot
            try:
                (pack_dir / "backup_settings.json").write_text(json.dumps(settings.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

        finally:
            if settings.ragflow_stop_services:
                try:
                    self.store.update_job(job_id, message="启动 RAGFlow 服务（可选）", progress=96)
                    docker_compose_start(compose_file)
                except Exception:
                    pass

        backup_done_ms = int(time.time() * 1000)
        # Keep job running while we perform post-backup steps (replication).
        self.store.update_job(job_id, status="running", progress=90, message="备份完成，准备同步")
        try:
            if job_kind == "full":
                self.store.update_last_full_backup_time(backup_done_ms)
            elif job_kind == "incremental":
                self.store.update_last_incremental_backup_time(backup_done_ms)
        except Exception:
            # Best-effort: backup succeeded; scheduling metadata must not fail the job.
            pass

        # Automatic replication to mounted SMB share
        replicated = False
        try:
            from .replica_service import BackupReplicaService
            replica_svc = BackupReplicaService(self.store)
            replicated = bool(replica_svc.replicate_backup(pack_dir, job_id))
        except Exception as e:
            # Replication failure should not mark the backup as failed
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Replication failed: {e}", exc_info=True)
            # Update message to indicate replication failure, but keep status as "completed"
            try:
                self.store.update_job(
                    job_id,
                    message=f"备份完成（同步失败：{str(e)}）",
                    detail=str(e),
                    progress=100
                )
            except Exception:
                pass
        finally:
            finished_at_ms = int(time.time() * 1000)
            # If replication is disabled, or replication didn't update the progress to 100, finish the job here.
            try:
                if not replicated:
                    # Keep any error message written by replica service; only set a default if still at the pre-sync message.
                    try:
                        current = self.store.get_job(job_id)
                        if (current.message or "") == "备份完成，准备同步":
                            self.store.update_job(job_id, message="备份完成")
                    except Exception:
                        pass
                self.store.update_job(job_id, status="completed", progress=100, finished_at_ms=finished_at_ms)
            except Exception:
                pass

    def run_incremental_backup_job(self, job_id: int) -> None:
        """
        Incremental backup:
        - Excludes Docker images to keep runtime/size manageable.
        """
        self.run_job(job_id, include_images=False)

    def run_full_backup_job(self, job_id: int) -> None:
        """
        Full backup:
        - Respects `full_backup_include_images` in settings.
        """
        settings = self.store.get_settings()
        self.run_job(job_id, include_images=bool(getattr(settings, "full_backup_include_images", 1)))

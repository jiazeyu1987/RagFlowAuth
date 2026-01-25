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

    def run_job(self, job_id: int) -> None:
        settings = self.store.get_settings()
        target = settings.target_path()
        if not target:
            raise RuntimeError("未配置备份目标（请设置目标电脑IP/共享目录，或选择本地目录）")

        ok, why = docker_ok()
        if not ok:
            raise RuntimeError(f"Docker 不可用：{why}")

        now_ms = int(time.time() * 1000)
        self.store.update_job(job_id, status="running", progress=1, message="开始备份", started_at_ms=now_ms)

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
        sqlite_online_backup(src_db, pack_dir / "auth.db")
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
                docker_tar_volume(v, pack_dir / "volumes" / f"{v}.tar.gz")
                prog += step

            # 3) images (optional)
            if getattr(settings, "full_backup_include_images", 1):
                images, err = list_compose_images(compose_file)
                if err:
                    self.store.update_job(job_id, message=f"跳过镜像备份：{err}", progress=min(95, prog))
                else:
                    ok_save, err2 = docker_save_images(images, pack_dir / "images.tar")
                    if not ok_save and err2:
                        self.store.update_job(job_id, message=f"镜像备份失败（已跳过）：{err2}", progress=min(95, prog))
                    else:
                        self.store.update_job(job_id, message=f"镜像已备份（{len(images)}）", progress=min(95, prog))

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

        self.store.update_job(job_id, status="completed", progress=100, message="备份完成", finished_at_ms=int(time.time() * 1000))


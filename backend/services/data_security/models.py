from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DataSecuritySettings:
    enabled: bool
    interval_minutes: int
    target_mode: str  # share | local
    target_ip: str | None
    target_share_name: str | None
    target_subdir: str | None
    target_local_dir: str | None
    ragflow_compose_path: str | None
    ragflow_project_name: str | None
    ragflow_stop_services: bool
    auth_db_path: str
    updated_at_ms: int
    last_run_at_ms: int | None
    # 新增：备份后上传到远程服务器
    upload_after_backup: bool
    upload_host: str | None
    upload_username: str | None
    upload_target_path: str | None
    # 全量备份
    full_backup_enabled: bool
    full_backup_include_images: bool
    # Cron-based scheduling
    incremental_schedule: str | None  # Cron expression for incremental backups
    full_backup_schedule: str | None  # Cron expression for full backups
    # Last successful backup times (for reliable scheduling)
    last_incremental_backup_time_ms: int | None
    last_full_backup_time_ms: int | None

    def target_path(self) -> str | None:
        if self.target_mode == "local":
            return self.target_local_dir
        ip = (self.target_ip or "").strip()
        share = (self.target_share_name or "").strip().strip("\\/")
        subdir = (self.target_subdir or "").strip().strip("\\/")
        if not ip or not share:
            return None
        return f"\\\\{ip}\\{share}\\{subdir}" if subdir else f"\\\\{ip}\\{share}"


@dataclass(frozen=True)
class BackupJob:
    id: int
    kind: str
    status: str
    progress: int
    message: str | None
    detail: str | None
    output_dir: str | None
    created_at_ms: int
    started_at_ms: int | None
    finished_at_ms: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "detail": self.detail,
            "output_dir": self.output_dir,
            "created_at_ms": self.created_at_ms,
            "started_at_ms": self.started_at_ms,
            "finished_at_ms": self.finished_at_ms,
        }

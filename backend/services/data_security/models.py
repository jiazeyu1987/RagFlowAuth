from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from backend.app.core.managed_paths import managed_data_root
from backend.app.core.paths import repo_root


LOCAL_BACKUP_TARGET_PATH = "/app/data/backups"
STANDARD_REPLICA_MOUNT_ROOT = "/mnt/replica"


def _normalize_path_text(path_text: str | None) -> str:
    text = str(path_text or "").strip().replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    if text.startswith("/") and len(text) > 1:
        text = text.rstrip("/")
    return text


def _is_standard_replica_path(path_text: str | None) -> bool:
    text = _normalize_path_text(path_text)
    if not text.startswith("/"):
        return False
    return text == STANDARD_REPLICA_MOUNT_ROOT or text.startswith(STANDARD_REPLICA_MOUNT_ROOT + "/")


def _running_inside_container() -> bool:
    return Path("/.dockerenv").exists()


def resolve_runtime_managed_path(path_text: str | None) -> str | None:
    text = _normalize_path_text(path_text)
    if not text:
        return None
    if not text.startswith("/"):
        return str(Path(str(path_text)))
    if _running_inside_container():
        return text

    pure = PurePosixPath(text)
    if text == "/app/data" or text.startswith("/app/data/"):
        rel = pure.relative_to(PurePosixPath("/app/data"))
        return str((managed_data_root() / Path(*rel.parts)).resolve())
    if text == "/app/uploads" or text.startswith("/app/uploads/"):
        rel = pure.relative_to(PurePosixPath("/app/uploads"))
        return str((managed_data_root() / "uploads" / Path(*rel.parts)).resolve())
    return str(Path(str(path_text)))


def resolve_runtime_compose_file_path(path_text: str | None) -> Path | None:
    raw = str(path_text or "").strip()
    text = _normalize_path_text(raw)
    if not text:
        return None
    if _running_inside_container():
        return Path(text if text.startswith("/") else raw)

    native = Path(raw)
    if native.is_absolute():
        return native

    if text.startswith("/"):
        pure = PurePosixPath(text)
        if text == "/app" or text.startswith("/app/"):
            rel = pure.relative_to(PurePosixPath("/app"))
            return (repo_root() / Path(*rel.parts)).resolve()
        return Path(raw)

    return (repo_root() / native).resolve()


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
    # Retention
    backup_retention_max: int
    # Cron-based scheduling
    incremental_schedule: str | None  # Cron expression for incremental backups
    full_backup_schedule: str | None  # Cron expression for full backups
    # Last successful backup times (for reliable scheduling)
    last_incremental_backup_time_ms: int | None
    last_full_backup_time_ms: int | None
    # Automatic replication to mounted SMB share
    replica_enabled: bool
    replica_target_path: str | None
    replica_subdir_format: str  # 'flat' or 'date'
    standard_replica_mount_active: bool = False

    def local_backup_target_path(self) -> str:
        return str(resolve_runtime_managed_path(LOCAL_BACKUP_TARGET_PATH) or LOCAL_BACKUP_TARGET_PATH)

    def target_path(self) -> str | None:
        if self.target_mode == "local":
            local_target = str(self.target_local_dir or "").strip()
            if not local_target:
                return None
            if _is_standard_replica_path(local_target) and not self.standard_replica_mount_active:
                return None
            return local_target
        ip = (self.target_ip or "").strip()
        share = (self.target_share_name or "").strip().strip("\\/")
        subdir = (self.target_subdir or "").strip().strip("\\/")
        if not ip or not share:
            return None
        return f"\\\\{ip}\\{share}\\{subdir}" if subdir else f"\\\\{ip}\\{share}"

    def windows_target_path(self) -> str | None:
        replica_target = str(self.replica_target_path or "").strip()
        if replica_target and (
            self.standard_replica_mount_active or not _is_standard_replica_path(replica_target)
        ):
            return replica_target
        return self.target_path()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["resolved_local_backup_target_path"] = self.local_backup_target_path()
        data["resolved_target_path"] = self.target_path()
        data["resolved_windows_target_path"] = self.windows_target_path()
        return data


@dataclass(frozen=True)
class BackupJob:
    id: int
    kind: str
    status: str
    progress: int
    message: str | None
    detail: str | None
    output_dir: str | None
    package_hash: str | None
    verified_by: str | None
    verified_at_ms: int | None
    created_at_ms: int
    started_at_ms: int | None
    finished_at_ms: int | None
    replication_status: str | None = None
    replication_error: str | None = None
    replica_path: str | None = None
    verification_status: str | None = None
    verification_detail: str | None = None
    last_restore_drill_id: str | None = None
    cancel_requested_at_ms: int | None = None
    cancel_reason: str | None = None
    canceled_at_ms: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "detail": self.detail,
            "output_dir": self.output_dir,
            "package_hash": self.package_hash,
            "verified_by": self.verified_by,
            "verified_at_ms": self.verified_at_ms,
            "replication_status": self.replication_status,
            "replication_error": self.replication_error,
            "replica_path": self.replica_path,
            "verification_status": self.verification_status,
            "verification_detail": self.verification_detail,
            "last_restore_drill_id": self.last_restore_drill_id,
            "created_at_ms": self.created_at_ms,
            "started_at_ms": self.started_at_ms,
            "finished_at_ms": self.finished_at_ms,
            "cancel_requested_at_ms": self.cancel_requested_at_ms,
            "cancel_reason": self.cancel_reason,
            "canceled_at_ms": self.canceled_at_ms,
        }


@dataclass(frozen=True)
class RestoreDrill:
    drill_id: str
    job_id: int
    backup_path: str
    backup_hash: str
    actual_backup_hash: str | None
    hash_match: bool
    restore_target: str
    restored_auth_db_path: str | None
    restored_auth_db_hash: str | None
    compare_match: bool
    package_validation_status: str | None
    acceptance_status: str | None
    executed_by: str
    executed_at_ms: int
    result: str
    verification_notes: str | None
    verification_report: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "drill_id": self.drill_id,
            "job_id": self.job_id,
            "backup_path": self.backup_path,
            "backup_hash": self.backup_hash,
            "actual_backup_hash": self.actual_backup_hash,
            "hash_match": self.hash_match,
            "restore_target": self.restore_target,
            "restored_auth_db_path": self.restored_auth_db_path,
            "restored_auth_db_hash": self.restored_auth_db_hash,
            "compare_match": self.compare_match,
            "package_validation_status": self.package_validation_status,
            "acceptance_status": self.acceptance_status,
            "executed_by": self.executed_by,
            "executed_at_ms": self.executed_at_ms,
            "result": self.result,
            "verification_notes": self.verification_notes,
            "verification_report": self.verification_report or {},
        }

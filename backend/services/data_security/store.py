from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import time
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite
from backend.services.config_change_log_store import ConfigChangeLogStore

from .models import BackupJob, DataSecuritySettings, RestoreDrill
from .repositories import (
    BackupJobRepository,
    BackupLockRepository,
    DataSecuritySettingsRepository,
    RestoreDrillRepository,
)
from .settings_policy import DataSecuritySettingsPolicy


class DataSecurityStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_owner = uuid4().hex
        self._settings_policy = DataSecuritySettingsPolicy()
        self._lock_repository = BackupLockRepository(self._conn, lock_owner=self._lock_owner)
        self._settings_repository = DataSecuritySettingsRepository(self._conn)
        self._job_repository = BackupJobRepository(self._conn)
        self._restore_drill_repository = RestoreDrillRepository(self._conn)

    def _conn(self):
        return connect_sqlite(self.db_path)

    def try_acquire_backup_lock(self, *, job_id: int | None = None, ttl_ms: int = 24 * 60 * 60 * 1000) -> bool:
        return self._lock_repository.acquire_lock(name="backup", job_id=job_id, ttl_ms=ttl_ms)

    def release_backup_lock(self, *, job_id: int | None = None, force: bool = False) -> None:
        self._lock_repository.release_lock(name="backup", job_id=job_id, force=force)

    def get_active_job_id(self) -> int | None:
        return self._job_repository.get_active_job_id()

    def get_settings(self) -> DataSecuritySettings:
        record = self._settings_repository.get_settings_record()
        return self._settings_policy.build_settings(record)

    def update_settings(
        self,
        updates: dict[str, Any],
        *,
        changed_by: str | None = None,
        change_reason: str | None = None,
        approved_by: str | None = None,
    ) -> DataSecuritySettings:
        now_ms = int(time.time() * 1000)
        before = self.get_settings()
        fields = self._settings_repository.prepare_updates(updates)
        if not fields:
            raise ValueError("no_settings_changes")

        fields = self._settings_policy.constrain_updates(fields)
        fields["updated_at_ms"] = now_ms
        self._settings_repository.update_settings(fields)
        updated = self.get_settings()

        if changed_by is not None or change_reason is not None or approved_by is not None:
            if not str(changed_by or "").strip():
                raise ValueError("changed_by_required")
            if not str(change_reason or "").strip():
                raise ValueError("change_reason_required")
            ConfigChangeLogStore(db_path=self.db_path).log_change(
                config_domain="data_security_settings",
                before=asdict(before),
                after=asdict(updated),
                changed_by=str(changed_by).strip(),
                change_reason=str(change_reason).strip(),
                approved_by=(str(approved_by).strip() or None) if approved_by is not None else None,
            )

        return updated

    def touch_last_run(self, when_ms: int | None = None) -> None:
        self._settings_repository.touch_last_run(when_ms)

    def update_last_incremental_backup_time(self, when_ms: int | None = None) -> None:
        self._settings_repository.update_last_incremental_backup_time(when_ms)

    def update_last_full_backup_time(self, when_ms: int | None = None) -> None:
        self._settings_repository.update_last_full_backup_time(when_ms)

    def create_job(self, *, status: str = "queued", message: str | None = None, detail: str | None = None) -> BackupJob:
        return self._job_repository.create_job(kind="incremental", status=status, message=message, detail=detail)

    def create_job_v2(
        self,
        *,
        kind: str,
        status: str = "queued",
        message: str | None = None,
        detail: str | None = None,
    ) -> BackupJob:
        return self._job_repository.create_job(kind=kind, status=status, message=message, detail=detail)

    def update_job(
        self,
        job_id: int,
        *,
        status: str | None = None,
        progress: int | None = None,
        message: str | None = None,
        detail: str | None = None,
        output_dir: str | None = None,
        package_hash: str | None = None,
        verified_by: str | None = None,
        verified_at_ms: int | None = None,
        replication_status: str | None = None,
        replication_error: str | None = None,
        replica_path: str | None = None,
        verification_status: str | None = None,
        verification_detail: str | None = None,
        last_restore_drill_id: str | None = None,
        started_at_ms: int | None = None,
        finished_at_ms: int | None = None,
    ) -> BackupJob:
        return self._job_repository.update_job(
            job_id,
            status=status,
            progress=progress,
            message=message,
            detail=detail,
            output_dir=output_dir,
            package_hash=package_hash,
            verified_by=verified_by,
            verified_at_ms=verified_at_ms,
            replication_status=replication_status,
            replication_error=replication_error,
            replica_path=replica_path,
            verification_status=verification_status,
            verification_detail=verification_detail,
            last_restore_drill_id=last_restore_drill_id,
            started_at_ms=started_at_ms,
            finished_at_ms=finished_at_ms,
        )

    def request_cancel_job(self, job_id: int, *, reason: str | None = None) -> BackupJob:
        return self._job_repository.request_cancel(job_id, reason=reason)

    def is_cancel_requested(self, job_id: int) -> bool:
        return self._job_repository.is_cancel_requested(job_id)

    def mark_job_canceled(self, job_id: int, *, message: str | None = None, detail: str | None = None) -> BackupJob:
        return self._job_repository.mark_canceled(job_id, message=message, detail=detail)

    def get_job(self, job_id: int) -> BackupJob:
        return self._job_repository.get_job(job_id)

    def list_jobs(self, *, limit: int = 30) -> list[BackupJob]:
        return self._job_repository.list_jobs(limit=limit)

    def create_restore_drill(
        self,
        *,
        job_id: int,
        backup_path: str,
        backup_hash: str,
        actual_backup_hash: str | None,
        hash_match: bool,
        restore_target: str,
        restored_auth_db_path: str | None,
        restored_auth_db_hash: str | None,
        compare_match: bool,
        package_validation_status: str,
        acceptance_status: str,
        executed_by: str,
        executed_at_ms: int | None = None,
        result: str,
        verification_notes: str | None = None,
        verification_report: dict[str, Any] | None = None,
    ) -> RestoreDrill:
        self.get_job(int(job_id))
        when_ms = int(time.time() * 1000) if executed_at_ms is None else int(executed_at_ms)
        return self._restore_drill_repository.create_restore_drill(
            job_id=int(job_id),
            backup_path=backup_path,
            backup_hash=backup_hash,
            actual_backup_hash=actual_backup_hash,
            hash_match=hash_match,
            restore_target=restore_target,
            restored_auth_db_path=restored_auth_db_path,
            restored_auth_db_hash=restored_auth_db_hash,
            compare_match=compare_match,
            package_validation_status=package_validation_status,
            acceptance_status=acceptance_status,
            executed_by=executed_by,
            executed_at_ms=when_ms,
            result=result,
            verification_notes=verification_notes,
            verification_report=verification_report,
        )

    def list_restore_drills(self, *, limit: int = 30) -> list[RestoreDrill]:
        return self._restore_drill_repository.list_restore_drills(limit=limit)

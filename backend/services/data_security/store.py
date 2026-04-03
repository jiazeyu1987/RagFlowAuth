from __future__ import annotations

from dataclasses import asdict
import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite
from backend.services.config_change_log_store import ConfigChangeLogStore
from backend.services.mount_utils import is_cifs_mounted

from .models import BackupJob, DataSecuritySettings, RestoreDrill


class DataSecurityStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_owner = uuid4().hex

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _has_standard_replica_mount() -> bool:
        # Avoid touching /mnt/replica directly (stat can block on broken CIFS).
        return is_cifs_mounted("/mnt/replica")

    def _acquire_lock(self, *, name: str, job_id: int | None, ttl_ms: int) -> bool:
        """
        Acquire a cross-process lock stored in sqlite.

        Uses `BEGIN IMMEDIATE` to ensure the check-and-set is atomic across processes.
        If the lock exists but is older than ttl_ms, it will be taken over.
        """
        name = str(name or "").strip() or "backup"
        now_ms = int(time.time() * 1000)
        ttl_ms = int(max(1, ttl_ms))

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT owner, acquired_at_ms FROM backup_locks WHERE name = ?", (name,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO backup_locks (name, owner, job_id, acquired_at_ms) VALUES (?, ?, ?, ?)",
                    (name, self._lock_owner, job_id, now_ms),
                )
                conn.commit()
                return True

            acquired_at_ms = int(row["acquired_at_ms"] or 0)
            if now_ms - acquired_at_ms > ttl_ms:
                conn.execute(
                    "UPDATE backup_locks SET owner = ?, job_id = ?, acquired_at_ms = ? WHERE name = ?",
                    (self._lock_owner, job_id, now_ms, name),
                )
                conn.commit()
                return True

            conn.rollback()
            return False
        finally:
            conn.close()

    def _release_lock(self, *, name: str) -> None:
        """Release lock by name (owner check removed to fix worker thread issue)."""
        name = str(name or "").strip() or "backup"
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM backup_locks WHERE name = ?", (name,))
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            conn.close()

    def try_acquire_backup_lock(self, *, job_id: int | None = None, ttl_ms: int = 24 * 60 * 60 * 1000) -> bool:
        return self._acquire_lock(name="backup", job_id=job_id, ttl_ms=ttl_ms)

    def release_backup_lock(self) -> None:
        self._release_lock(name="backup")

    def get_active_job_id(self) -> int | None:
        """Return the newest queued/running job id, if any."""
        try:
            for job in self.list_jobs(limit=5):
                if job.status in ("queued", "running"):
                    return int(job.id)
        except Exception:
            return None
        return None

    def get_settings(self) -> DataSecuritySettings:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM data_security_settings WHERE id = 1").fetchone()
            if not row:
                raise RuntimeError("data_security_settings not initialized")

            def get_col(key, default=None):
                try:
                    return row[key]
                except IndexError:
                    return default

            enabled = bool(row["enabled"])
            interval_minutes = int(row["interval_minutes"] or 1440)
            target_mode = str(row["target_mode"] or "share")
            target_ip = row["target_ip"]
            target_share_name = row["target_share_name"]
            target_subdir = row["target_subdir"]
            target_local_dir = row["target_local_dir"]
            ragflow_compose_path = row["ragflow_compose_path"]
            ragflow_project_name = row["ragflow_project_name"]
            ragflow_stop_services = bool(row["ragflow_stop_services"])
            auth_db_path = str(row["auth_db_path"] or "data/auth.db")
            full_backup_include_images = bool(get_col("full_backup_include_images", 1))
            try:
                backup_retention_max = int(get_col("backup_retention_max", 30) or 30)
            except Exception:
                backup_retention_max = 30
            backup_retention_max = max(1, min(100, backup_retention_max))
            replica_target_path = get_col("replica_target_path")

            # If the standard mount is present (Linux server / Docker), keep key backup paths fixed.
            # This prevents "environment drift" caused by UI edits and avoids writing large backups to `/`.
            if self._has_standard_replica_mount():
                target_mode = "local"
                target_local_dir = "/mnt/replica/RagflowAuth"
                target_ip = None
                target_share_name = None
                target_subdir = None
                replica_target_path = "/mnt/replica/RagflowAuth"

                # These paths are inside the backend container.
                ragflow_compose_path = "/app/ragflow_compose/docker-compose.yml"
                auth_db_path = "data/auth.db"

                # Full backup should include images on servers so it can be restored offline.
                full_backup_include_images = True

            return DataSecuritySettings(
                enabled=enabled,
                interval_minutes=interval_minutes,
                target_mode=target_mode,
                target_ip=target_ip,
                target_share_name=target_share_name,
                target_subdir=target_subdir,
                target_local_dir=target_local_dir,
                ragflow_compose_path=ragflow_compose_path,
                ragflow_project_name=ragflow_project_name,
                ragflow_stop_services=ragflow_stop_services,
                auth_db_path=auth_db_path,
                updated_at_ms=int(row["updated_at_ms"] or 0),
                last_run_at_ms=int(row["last_run_at_ms"]) if row["last_run_at_ms"] is not None else None,
                upload_after_backup=bool(get_col("upload_after_backup", 0)),
                upload_host=get_col("upload_host"),
                upload_username=get_col("upload_username"),
                upload_target_path=get_col("upload_target_path"),
                full_backup_enabled=bool(get_col("full_backup_enabled", 0)),
                full_backup_include_images=full_backup_include_images,
                backup_retention_max=backup_retention_max,
                incremental_schedule=get_col("incremental_schedule"),
                full_backup_schedule=get_col("full_backup_schedule"),
                last_incremental_backup_time_ms=int(get_col("last_incremental_backup_time_ms")) if get_col("last_incremental_backup_time_ms") is not None else None,
                last_full_backup_time_ms=int(get_col("last_full_backup_time_ms")) if get_col("last_full_backup_time_ms") is not None else None,
                replica_enabled=bool(get_col("replica_enabled", 0)),
                replica_target_path=replica_target_path,
                replica_subdir_format=get_col("replica_subdir_format") or "flat",
            )
        finally:
            conn.close()

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
        allowed = {
            "enabled",
            "interval_minutes",
            "target_mode",
            "target_ip",
            "target_share_name",
            "target_subdir",
            "target_local_dir",
            "ragflow_compose_path",
            "ragflow_project_name",
            "ragflow_stop_services",
            "auth_db_path",
            "full_backup_enabled",
            "full_backup_include_images",
            "backup_retention_max",
            "incremental_schedule",
            "full_backup_schedule",
            "replica_enabled",
            "replica_target_path",
            "replica_subdir_format",
        }
        fields = {k: updates.get(k) for k in allowed if k in updates}
        if not fields:
            raise ValueError("no_settings_changes")

        if "backup_retention_max" in fields:
            try:
                n = int(fields["backup_retention_max"])
                fields["backup_retention_max"] = max(1, min(100, n))
            except Exception:
                fields.pop("backup_retention_max", None)

        # If the standard mount is present (Linux server / Docker), keep key backup paths fixed.
        # This prevents UI mistakes from writing huge backups to `/` and avoids cross-env drift.
        if self._has_standard_replica_mount():
            fields["target_mode"] = "local"
            fields["target_local_dir"] = "/mnt/replica/RagflowAuth"
            fields["replica_target_path"] = "/mnt/replica/RagflowAuth"
            fields["ragflow_compose_path"] = "/app/ragflow_compose/docker-compose.yml"
            fields["auth_db_path"] = "data/auth.db"
            fields["full_backup_include_images"] = True
        fields["updated_at_ms"] = now_ms

        conn = self._conn()
        try:
            sets = ", ".join([f"{k} = ?" for k in fields.keys()])
            values = list(fields.values())
            conn.execute(f"UPDATE data_security_settings SET {sets} WHERE id = 1", values)
            conn.commit()
        finally:
            conn.close()
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
        now_ms = int(time.time() * 1000) if when_ms is None else int(when_ms)
        conn = self._conn()
        try:
            conn.execute("UPDATE data_security_settings SET last_run_at_ms = ? WHERE id = 1", (now_ms,))
            conn.commit()
        finally:
            conn.close()

    def update_last_incremental_backup_time(self, when_ms: int | None = None) -> None:
        """Update the last successful incremental backup time."""
        now_ms = int(time.time() * 1000) if when_ms is None else int(when_ms)
        conn = self._conn()
        try:
            conn.execute("UPDATE data_security_settings SET last_incremental_backup_time_ms = ? WHERE id = 1", (now_ms,))
            conn.commit()
        finally:
            conn.close()

    def update_last_full_backup_time(self, when_ms: int | None = None) -> None:
        """Update the last successful full backup time."""
        now_ms = int(time.time() * 1000) if when_ms is None else int(when_ms)
        conn = self._conn()
        try:
            conn.execute("UPDATE data_security_settings SET last_full_backup_time_ms = ? WHERE id = 1", (now_ms,))
            conn.commit()
        finally:
            conn.close()

    def create_job(self, *, status: str = "queued", message: str | None = None, detail: str | None = None) -> BackupJob:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO backup_jobs (kind, status, progress, message, detail, output_dir, created_at_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("incremental", status, 0, message, detail, None, now_ms),
            )
            job_id = int(cur.lastrowid)
            conn.commit()
        finally:
            conn.close()
        return self.get_job(job_id)

    def create_job_v2(
        self,
        *,
        kind: str,
        status: str = "queued",
        message: str | None = None,
        detail: str | None = None,
    ) -> BackupJob:
        kind = str(kind or "incremental")
        if kind not in ("incremental", "full"):
            kind = "incremental"
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO backup_jobs (kind, status, progress, message, detail, output_dir, created_at_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (kind, status, 0, message, detail, None, now_ms),
            )
            job_id = int(cur.lastrowid)
            conn.commit()
        finally:
            conn.close()
        return self.get_job(job_id)

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
        fields: dict[str, Any] = {}
        if status is not None:
            fields["status"] = status
        if progress is not None:
            fields["progress"] = int(max(0, min(100, progress)))
        if message is not None:
            fields["message"] = message
        if detail is not None:
            fields["detail"] = detail
        if output_dir is not None:
            fields["output_dir"] = output_dir
        if package_hash is not None:
            fields["package_hash"] = str(package_hash)
        if verified_by is not None:
            fields["verified_by"] = str(verified_by)
        if verified_at_ms is not None:
            fields["verified_at_ms"] = int(verified_at_ms)
        if replication_status is not None:
            fields["replication_status"] = str(replication_status)
        if replication_error is not None:
            fields["replication_error"] = str(replication_error)
        if replica_path is not None:
            fields["replica_path"] = str(replica_path)
        if verification_status is not None:
            fields["verification_status"] = str(verification_status)
        if verification_detail is not None:
            fields["verification_detail"] = str(verification_detail)
        if last_restore_drill_id is not None:
            fields["last_restore_drill_id"] = str(last_restore_drill_id)
        if started_at_ms is not None:
            fields["started_at_ms"] = int(started_at_ms)
        if finished_at_ms is not None:
            fields["finished_at_ms"] = int(finished_at_ms)

        if not fields:
            return self.get_job(job_id)

        conn = self._conn()
        try:
            sets = ", ".join([f"{k} = ?" for k in fields.keys()])
            values = list(fields.values())
            values.append(int(job_id))
            conn.execute(f"UPDATE backup_jobs SET {sets} WHERE id = ?", values)
            conn.commit()
        finally:
            conn.close()
        return self.get_job(job_id)

    def request_cancel_job(self, job_id: int, *, reason: str | None = None) -> BackupJob:
        """
        Request cooperative cancellation for a job.

        The running worker checks this flag at safe checkpoints and during long operations via heartbeat.
        """
        now_ms = int(time.time() * 1000)
        reason = (reason or "").strip() or "user_requested"
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE backup_jobs
                SET cancel_requested_at_ms = ?,
                    cancel_reason = ?,
                    status = CASE
                        WHEN status IN ('queued', 'running') THEN 'canceling'
                        ELSE status
                    END,
                    message = CASE
                        WHEN status IN ('queued', 'running') THEN '取消中...'
                        ELSE message
                    END
                WHERE id = ?
                """,
                (now_ms, reason, int(job_id)),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_job(int(job_id))

    def is_cancel_requested(self, job_id: int) -> bool:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT status, cancel_requested_at_ms FROM backup_jobs WHERE id = ?",
                (int(job_id),),
            ).fetchone()
            if not row:
                return False
            status = str(row["status"] or "")
            if status in ("canceling", "canceled"):
                return True
            return row["cancel_requested_at_ms"] is not None
        finally:
            conn.close()

    def mark_job_canceled(self, job_id: int, *, message: str | None = None, detail: str | None = None) -> BackupJob:
        now_ms = int(time.time() * 1000)
        message = message if message is not None else "已取消"
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE backup_jobs
                SET status = 'canceled',
                    progress = 100,
                    message = ?,
                    detail = ?,
                    canceled_at_ms = ?,
                    finished_at_ms = COALESCE(finished_at_ms, ?)
                WHERE id = ?
                """,
                (message, detail, now_ms, now_ms, int(job_id)),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_job(int(job_id))

    def get_job(self, job_id: int) -> BackupJob:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM backup_jobs WHERE id = ?", (int(job_id),)).fetchone()
            if not row:
                raise KeyError(f"job not found: {job_id}")

            def get_col(key: str, default=None):
                try:
                    return row[key]
                except Exception:
                    return default

            return BackupJob(
                id=int(row["id"]),
                kind=str(row["kind"] or "incremental"),
                status=str(row["status"]),
                progress=int(row["progress"] or 0),
                message=row["message"],
                detail=row["detail"],
                output_dir=row["output_dir"],
                package_hash=get_col("package_hash"),
                verified_by=get_col("verified_by"),
                verified_at_ms=(int(get_col("verified_at_ms")) if get_col("verified_at_ms") is not None else None),
                created_at_ms=int(row["created_at_ms"] or 0),
                started_at_ms=int(row["started_at_ms"]) if row["started_at_ms"] is not None else None,
                finished_at_ms=int(row["finished_at_ms"]) if row["finished_at_ms"] is not None else None,
                replication_status=get_col("replication_status"),
                replication_error=get_col("replication_error"),
                replica_path=get_col("replica_path"),
                verification_status=get_col("verification_status"),
                verification_detail=get_col("verification_detail"),
                last_restore_drill_id=get_col("last_restore_drill_id"),
                cancel_requested_at_ms=(
                    int(get_col("cancel_requested_at_ms")) if get_col("cancel_requested_at_ms") is not None else None
                ),
                cancel_reason=get_col("cancel_reason"),
                canceled_at_ms=(int(get_col("canceled_at_ms")) if get_col("canceled_at_ms") is not None else None),
            )
        finally:
            conn.close()

    def list_jobs(self, *, limit: int = 30) -> list[BackupJob]:
        limit = int(max(1, min(200, limit)))
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM backup_jobs ORDER BY created_at_ms DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                BackupJob(
                    id=int(r["id"]),
                    kind=str(r["kind"] or "incremental"),
                    status=str(r["status"]),
                    progress=int(r["progress"] or 0),
                    message=r["message"],
                    detail=r["detail"],
                    output_dir=r["output_dir"],
                    package_hash=(r["package_hash"] if "package_hash" in r.keys() else None),
                    verified_by=(r["verified_by"] if "verified_by" in r.keys() else None),
                    verified_at_ms=(
                        int(r["verified_at_ms"]) if "verified_at_ms" in r.keys() and r["verified_at_ms"] is not None else None
                    ),
                    created_at_ms=int(r["created_at_ms"] or 0),
                    started_at_ms=int(r["started_at_ms"]) if r["started_at_ms"] is not None else None,
                    finished_at_ms=int(r["finished_at_ms"]) if r["finished_at_ms"] is not None else None,
                    replication_status=(r["replication_status"] if "replication_status" in r.keys() else None),
                    replication_error=(r["replication_error"] if "replication_error" in r.keys() else None),
                    replica_path=(r["replica_path"] if "replica_path" in r.keys() else None),
                    verification_status=(r["verification_status"] if "verification_status" in r.keys() else None),
                    verification_detail=(r["verification_detail"] if "verification_detail" in r.keys() else None),
                    last_restore_drill_id=(r["last_restore_drill_id"] if "last_restore_drill_id" in r.keys() else None),
                    cancel_requested_at_ms=(
                        int(r["cancel_requested_at_ms"]) if "cancel_requested_at_ms" in r.keys() and r["cancel_requested_at_ms"] is not None else None
                    ),
                    cancel_reason=(r["cancel_reason"] if "cancel_reason" in r.keys() else None),
                    canceled_at_ms=(
                        int(r["canceled_at_ms"]) if "canceled_at_ms" in r.keys() and r["canceled_at_ms"] is not None else None
                    ),
                )
                for r in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def _restore_drill_from_row(row) -> RestoreDrill:
        report = row["verification_report_json"] if "verification_report_json" in row.keys() else None
        parsed_report = json.loads(report) if report else {}
        return RestoreDrill(
            drill_id=str(row["drill_id"]),
            job_id=int(row["job_id"]),
            backup_path=str(row["backup_path"]),
            backup_hash=str(row["backup_hash"]),
            actual_backup_hash=(str(row["actual_backup_hash"]) if row["actual_backup_hash"] is not None else None),
            hash_match=bool(int(row["hash_match"] or 0)),
            restore_target=str(row["restore_target"]),
            restored_auth_db_path=(
                str(row["restored_auth_db_path"]) if row["restored_auth_db_path"] is not None else None
            ),
            restored_auth_db_hash=(
                str(row["restored_auth_db_hash"]) if row["restored_auth_db_hash"] is not None else None
            ),
            compare_match=bool(int(row["compare_match"] or 0)),
            package_validation_status=(
                str(row["package_validation_status"]) if row["package_validation_status"] is not None else None
            ),
            acceptance_status=(str(row["acceptance_status"]) if row["acceptance_status"] is not None else None),
            executed_by=str(row["executed_by"]),
            executed_at_ms=int(row["executed_at_ms"] or 0),
            result=str(row["result"]),
            verification_notes=row["verification_notes"],
            verification_report=parsed_report,
        )

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
        job_id = int(job_id)
        self.get_job(job_id)

        backup_path = str(backup_path or "").strip()
        backup_hash = str(backup_hash or "").strip()
        restore_target = str(restore_target or "").strip()
        executed_by = str(executed_by or "").strip()
        result = str(result or "").strip().lower()

        if not backup_path:
            raise ValueError("backup_path_required")
        if not backup_hash:
            raise ValueError("backup_hash_required")
        if not restore_target:
            raise ValueError("restore_target_required")
        if not executed_by:
            raise ValueError("executed_by_required")
        if result not in ("success", "failed"):
            raise ValueError("invalid_restore_result")
        if package_validation_status not in ("passed", "failed", "blocked"):
            raise ValueError("invalid_package_validation_status")
        if acceptance_status not in ("passed", "failed", "blocked"):
            raise ValueError("invalid_acceptance_status")

        when_ms = int(time.time() * 1000) if executed_at_ms is None else int(executed_at_ms)
        drill_id = f"restore_drill_{uuid4().hex}"
        report_json = json.dumps(verification_report or {}, ensure_ascii=False, sort_keys=True)

        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO restore_drills (
                    drill_id,
                    job_id,
                    backup_path,
                    backup_hash,
                    actual_backup_hash,
                    hash_match,
                    restore_target,
                    restored_auth_db_path,
                    restored_auth_db_hash,
                    compare_match,
                    package_validation_status,
                    acceptance_status,
                    executed_by,
                    executed_at_ms,
                    result,
                    verification_notes,
                    verification_report_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    drill_id,
                    job_id,
                    backup_path,
                    backup_hash,
                    actual_backup_hash,
                    1 if hash_match else 0,
                    restore_target,
                    restored_auth_db_path,
                    restored_auth_db_hash,
                    1 if compare_match else 0,
                    package_validation_status,
                    acceptance_status,
                    executed_by,
                    when_ms,
                    result,
                    verification_notes,
                    report_json,
                ),
            )
            if acceptance_status == "passed":
                conn.execute(
                    """
                    UPDATE backup_jobs
                    SET
                        verified_by = ?,
                        verified_at_ms = ?,
                        verification_status = 'passed',
                        verification_detail = ?,
                        last_restore_drill_id = ?
                    WHERE id = ?
                    """,
                    (
                        executed_by,
                        when_ms,
                        str(verification_notes or ""),
                        drill_id,
                        job_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE backup_jobs
                    SET
                        verification_status = ?,
                        verification_detail = ?,
                        last_restore_drill_id = ?
                    WHERE id = ?
                    """,
                    (
                        acceptance_status,
                        str(verification_notes or ""),
                        drill_id,
                        job_id,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM restore_drills WHERE drill_id = ?", (drill_id,)).fetchone()
            if not row:
                raise RuntimeError("restore_drill_not_found_after_create")
            return self._restore_drill_from_row(row)
        finally:
            conn.close()

    def list_restore_drills(self, *, limit: int = 30) -> list[RestoreDrill]:
        limit = int(max(1, min(200, limit)))
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT *
                FROM restore_drills
                ORDER BY executed_at_ms DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._restore_drill_from_row(row) for row in rows]
        finally:
            conn.close()

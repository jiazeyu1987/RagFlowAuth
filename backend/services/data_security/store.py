from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

from .models import BackupJob, DataSecuritySettings


class DataSecurityStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_owner = uuid4().hex

    def _conn(self):
        return connect_sqlite(self.db_path)

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

            return DataSecuritySettings(
                enabled=bool(row["enabled"]),
                interval_minutes=int(row["interval_minutes"] or 1440),
                target_mode=str(row["target_mode"] or "share"),
                target_ip=row["target_ip"],
                target_share_name=row["target_share_name"],
                target_subdir=row["target_subdir"],
                target_local_dir=row["target_local_dir"],
                ragflow_compose_path=row["ragflow_compose_path"],
                ragflow_project_name=row["ragflow_project_name"],
                ragflow_stop_services=bool(row["ragflow_stop_services"]),
                auth_db_path=str(row["auth_db_path"] or "data/auth.db"),
                updated_at_ms=int(row["updated_at_ms"] or 0),
                last_run_at_ms=int(row["last_run_at_ms"]) if row["last_run_at_ms"] is not None else None,
                upload_after_backup=bool(get_col("upload_after_backup", 0)),
                upload_host=get_col("upload_host"),
                upload_username=get_col("upload_username"),
                upload_target_path=get_col("upload_target_path"),
                full_backup_enabled=bool(get_col("full_backup_enabled", 0)),
                full_backup_include_images=bool(get_col("full_backup_include_images", 1)),
                incremental_schedule=get_col("incremental_schedule"),
                full_backup_schedule=get_col("full_backup_schedule"),
                last_incremental_backup_time_ms=int(get_col("last_incremental_backup_time_ms")) if get_col("last_incremental_backup_time_ms") is not None else None,
                last_full_backup_time_ms=int(get_col("last_full_backup_time_ms")) if get_col("last_full_backup_time_ms") is not None else None,
                replica_enabled=bool(get_col("replica_enabled", 0)),
                replica_target_path=get_col("replica_target_path"),
                replica_subdir_format=get_col("replica_subdir_format") or "flat",
            )
        finally:
            conn.close()

    def update_settings(self, updates: dict[str, Any]) -> DataSecuritySettings:
        now_ms = int(time.time() * 1000)
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
            "incremental_schedule",
            "full_backup_schedule",
            "replica_enabled",
            "replica_target_path",
            "replica_subdir_format",
        }
        fields = {k: updates.get(k) for k in allowed if k in updates}
        # Replica target path is fixed to avoid drift/misconfig between systems.
        # It must match the mount point used by the server tools and the backend replication check.
        if "replica_target_path" in fields or "replica_enabled" in fields:
            fields["replica_target_path"] = "/mnt/replica/RagflowAuth"
        fields["updated_at_ms"] = now_ms

        conn = self._conn()
        try:
            sets = ", ".join([f"{k} = ?" for k in fields.keys()])
            values = list(fields.values())
            conn.execute(f"UPDATE data_security_settings SET {sets} WHERE id = 1", values)
            conn.commit()
        finally:
            conn.close()
        return self.get_settings()

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

    def get_job(self, job_id: int) -> BackupJob:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM backup_jobs WHERE id = ?", (int(job_id),)).fetchone()
            if not row:
                raise KeyError(f"job not found: {job_id}")
            return BackupJob(
                id=int(row["id"]),
                kind=str(row["kind"] or "incremental"),
                status=str(row["status"]),
                progress=int(row["progress"] or 0),
                message=row["message"],
                detail=row["detail"],
                output_dir=row["output_dir"],
                created_at_ms=int(row["created_at_ms"] or 0),
                started_at_ms=int(row["started_at_ms"]) if row["started_at_ms"] is not None else None,
                finished_at_ms=int(row["finished_at_ms"]) if row["finished_at_ms"] is not None else None,
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
                    created_at_ms=int(r["created_at_ms"] or 0),
                    started_at_ms=int(r["started_at_ms"]) if r["started_at_ms"] is not None else None,
                    finished_at_ms=int(r["finished_at_ms"]) if r["finished_at_ms"] is not None else None,
                )
                for r in rows
            ]
        finally:
            conn.close()

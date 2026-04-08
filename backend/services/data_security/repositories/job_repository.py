from __future__ import annotations

import time
from typing import Any, Callable

from ..models import BackupJob


class BackupJobRepository:
    def __init__(self, conn_factory: Callable[[], object]) -> None:
        self._conn_factory = conn_factory

    @staticmethod
    def _row_value(row: Any, key: str, default: Any = None) -> Any:
        try:
            return row[key]
        except Exception:
            return default

    @classmethod
    def _to_job(cls, row: Any) -> BackupJob:
        return BackupJob(
            id=int(row["id"]),
            kind=str(row["kind"] or "incremental"),
            status=str(row["status"]),
            progress=int(row["progress"] or 0),
            message=row["message"],
            detail=row["detail"],
            output_dir=row["output_dir"],
            package_hash=cls._row_value(row, "package_hash"),
            verified_by=cls._row_value(row, "verified_by"),
            verified_at_ms=(
                int(cls._row_value(row, "verified_at_ms")) if cls._row_value(row, "verified_at_ms") is not None else None
            ),
            created_at_ms=int(row["created_at_ms"] or 0),
            started_at_ms=int(row["started_at_ms"]) if row["started_at_ms"] is not None else None,
            finished_at_ms=int(row["finished_at_ms"]) if row["finished_at_ms"] is not None else None,
            replication_status=cls._row_value(row, "replication_status"),
            replication_error=cls._row_value(row, "replication_error"),
            replica_path=cls._row_value(row, "replica_path"),
            verification_status=cls._row_value(row, "verification_status"),
            verification_detail=cls._row_value(row, "verification_detail"),
            last_restore_drill_id=cls._row_value(row, "last_restore_drill_id"),
            cancel_requested_at_ms=(
                int(cls._row_value(row, "cancel_requested_at_ms"))
                if cls._row_value(row, "cancel_requested_at_ms") is not None
                else None
            ),
            cancel_reason=cls._row_value(row, "cancel_reason"),
            canceled_at_ms=(
                int(cls._row_value(row, "canceled_at_ms")) if cls._row_value(row, "canceled_at_ms") is not None else None
            ),
        )

    def create_job(
        self,
        *,
        kind: str,
        status: str = "queued",
        message: str | None = None,
        detail: str | None = None,
    ) -> BackupJob:
        normalized_kind = str(kind or "incremental")
        if normalized_kind not in ("incremental", "full"):
            normalized_kind = "incremental"

        now_ms = int(time.time() * 1000)
        conn = self._conn_factory()
        try:
            cur = conn.execute(
                """
                INSERT INTO backup_jobs (kind, status, progress, message, detail, output_dir, created_at_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (normalized_kind, status, 0, message, detail, None, now_ms),
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

        conn = self._conn_factory()
        try:
            sets = ", ".join([f"{key} = ?" for key in fields.keys()])
            values = list(fields.values()) + [int(job_id)]
            conn.execute(f"UPDATE backup_jobs SET {sets} WHERE id = ?", values)
            conn.commit()
        finally:
            conn.close()
        return self.get_job(job_id)

    def request_cancel(self, job_id: int, *, reason: str | None = None) -> BackupJob:
        now_ms = int(time.time() * 1000)
        cancel_reason = (reason or "").strip() or "user_requested"
        conn = self._conn_factory()
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
                (now_ms, cancel_reason, int(job_id)),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_job(int(job_id))

    def is_cancel_requested(self, job_id: int) -> bool:
        conn = self._conn_factory()
        try:
            row = conn.execute(
                "SELECT status, cancel_requested_at_ms FROM backup_jobs WHERE id = ?",
                (int(job_id),),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return False
        status = str(row["status"] or "")
        if status in ("canceling", "canceled"):
            return True
        return row["cancel_requested_at_ms"] is not None

    def mark_canceled(self, job_id: int, *, message: str | None = None, detail: str | None = None) -> BackupJob:
        now_ms = int(time.time() * 1000)
        final_message = message if message is not None else "已取消"
        conn = self._conn_factory()
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
                (final_message, detail, now_ms, now_ms, int(job_id)),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_job(int(job_id))

    def get_job(self, job_id: int) -> BackupJob:
        conn = self._conn_factory()
        try:
            row = conn.execute("SELECT * FROM backup_jobs WHERE id = ?", (int(job_id),)).fetchone()
        finally:
            conn.close()
        if not row:
            raise KeyError(f"job not found: {job_id}")
        return self._to_job(row)

    def list_jobs(self, *, limit: int = 30) -> list[BackupJob]:
        clamped_limit = int(max(1, min(200, limit)))
        conn = self._conn_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM backup_jobs ORDER BY created_at_ms DESC LIMIT ?",
                (clamped_limit,),
            ).fetchall()
        finally:
            conn.close()
        return [self._to_job(row) for row in rows]

    def get_active_job_id(self) -> int | None:
        conn = self._conn_factory()
        try:
            row = conn.execute(
                """
                SELECT id
                FROM backup_jobs
                WHERE status IN ('queued', 'running')
                ORDER BY created_at_ms DESC
                LIMIT 1
                """
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        return int(row["id"])

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


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
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "detail": self.detail,
            "output_dir": self.output_dir,
            "created_at_ms": self.created_at_ms,
            "started_at_ms": self.started_at_ms,
            "finished_at_ms": self.finished_at_ms,
        }


class DataSecurityStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    def get_settings(self) -> DataSecuritySettings:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM data_security_settings WHERE id = 1").fetchone()
            if not row:
                raise RuntimeError("data_security_settings not initialized")

            # Helper to safely get column value with default
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
        }
        fields = {k: updates.get(k) for k in allowed if k in updates}
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

    def create_job(self, *, status: str = "queued", message: str | None = None, detail: str | None = None) -> BackupJob:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO backup_jobs (status, progress, message, detail, output_dir, created_at_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (status, 0, message, detail, None, now_ms),
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


from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass
class NasImportTask:
    task_id: str
    folder_path: str
    kb_ref: str
    created_by_user_id: str
    total_files: int
    processed_files: int
    imported_count: int
    skipped_count: int
    failed_count: int
    status: str
    current_file: str
    error: str
    imported: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    failed: list[dict[str, Any]]
    pending_files: list[str]
    priority: int
    retry_count: int
    cancel_requested_at_ms: int | None
    created_at_ms: int
    updated_at_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "folder_path": self.folder_path,
            "kb_ref": self.kb_ref,
            "created_by_user_id": self.created_by_user_id,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "imported_count": self.imported_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "status": self.status,
            "current_file": self.current_file,
            "error": self.error,
            "imported": self.imported,
            "skipped": self.skipped,
            "failed": self.failed,
            "pending_files": self.pending_files,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "cancel_requested_at_ms": self.cancel_requested_at_ms,
            "created_at_ms": self.created_at_ms,
            "updated_at_ms": self.updated_at_ms,
        }


class NasTaskStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _decode_json(value: Any) -> list[dict[str, Any]]:
        raw = str(value or "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    @staticmethod
    def _encode_json(value: list[dict[str, Any]]) -> str:
        return json.dumps(value or [], ensure_ascii=False)

    @staticmethod
    def _decode_path_list(value: Any) -> list[str]:
        raw = str(value or "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        paths: list[str] = []
        for item in data:
            if isinstance(item, str):
                path = item.strip()
            elif isinstance(item, dict):
                path = str(item.get("path") or "").strip()
            else:
                path = str(item or "").strip()
            if path:
                paths.append(path)
        return paths

    @staticmethod
    def _encode_path_list(paths: list[str]) -> str:
        normalized = []
        for item in paths or []:
            path = str(item or "").strip()
            if path:
                normalized.append(path)
        return json.dumps(normalized, ensure_ascii=False)

    @classmethod
    def _from_row(cls, row) -> NasImportTask:
        return NasImportTask(
            task_id=str(row["task_id"]),
            folder_path=str(row["folder_path"] or ""),
            kb_ref=str(row["kb_ref"] or ""),
            created_by_user_id=str(row["created_by_user_id"] or ""),
            total_files=int(row["total_files"] or 0),
            processed_files=int(row["processed_files"] or 0),
            imported_count=int(row["imported_count"] or 0),
            skipped_count=int(row["skipped_count"] or 0),
            failed_count=int(row["failed_count"] or 0),
            status=str(row["status"] or "pending"),
            current_file=str(row["current_file"] or ""),
            error=str(row["error"] or ""),
            imported=cls._decode_json(row["imported_json"]),
            skipped=cls._decode_json(row["skipped_json"]),
            failed=cls._decode_json(row["failed_json"]),
            pending_files=cls._decode_path_list(row["pending_files_json"]),
            priority=int(row["priority"] or 100),
            retry_count=int(row["retry_count"] or 0),
            cancel_requested_at_ms=(
                int(row["cancel_requested_at_ms"]) if row["cancel_requested_at_ms"] is not None else None
            ),
            created_at_ms=int(row["created_at_ms"] or 0),
            updated_at_ms=int(row["updated_at_ms"] or 0),
        )

    def create_task(
        self,
        *,
        task_id: str,
        folder_path: str,
        kb_ref: str,
        created_by_user_id: str = "",
        total_files: int,
        processed_files: int = 0,
        imported_count: int = 0,
        skipped_count: int = 0,
        failed_count: int = 0,
        status: str = "pending",
        current_file: str = "",
        error: str = "",
        imported: list[dict[str, Any]] | None = None,
        skipped: list[dict[str, Any]] | None = None,
        failed: list[dict[str, Any]] | None = None,
        pending_files: list[str] | None = None,
        priority: int = 100,
        retry_count: int = 0,
        cancel_requested_at_ms: int | None = None,
    ) -> NasImportTask:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO nas_import_tasks (
                    task_id, folder_path, kb_ref, created_by_user_id, total_files, processed_files,
                    imported_count, skipped_count, failed_count, status,
                    current_file, error, imported_json, skipped_json, failed_json, pending_files_json,
                    priority,
                    retry_count, cancel_requested_at_ms,
                    created_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    folder_path,
                    kb_ref,
                    str(created_by_user_id or ""),
                    int(total_files),
                    int(processed_files),
                    int(imported_count),
                    int(skipped_count),
                    int(failed_count),
                    status,
                    current_file,
                    error,
                    self._encode_json(imported or []),
                    self._encode_json(skipped or []),
                    self._encode_json(failed or []),
                    self._encode_path_list(pending_files or []),
                    int(priority),
                    int(retry_count),
                    cancel_requested_at_ms,
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_task(task_id)

    def list_tasks_by_statuses(self, statuses: list[str], *, limit: int = 200) -> list[NasImportTask]:
        normalized = [str(item or "").strip() for item in statuses if str(item or "").strip()]
        if not normalized:
            return []
        placeholders = ", ".join(["?"] * len(normalized))
        conn = self._conn()
        try:
            rows = conn.execute(
                f"""
                SELECT * FROM nas_import_tasks
                WHERE status IN ({placeholders})
                ORDER BY updated_at_ms ASC
                LIMIT ?
                """,
                (*normalized, int(limit)),
            ).fetchall()
        finally:
            conn.close()
        return [self._from_row(row) for row in rows or []]

    def list_tasks(self, *, limit: int = 200, statuses: list[str] | None = None) -> list[NasImportTask]:
        safe_limit = int(max(1, min(2000, int(limit))))
        normalized_statuses = [str(item or "").strip() for item in (statuses or []) if str(item or "").strip()]
        conn = self._conn()
        try:
            if normalized_statuses:
                placeholders = ", ".join(["?"] * len(normalized_statuses))
                rows = conn.execute(
                    f"""
                    SELECT * FROM nas_import_tasks
                    WHERE status IN ({placeholders})
                    ORDER BY updated_at_ms DESC
                    LIMIT ?
                    """,
                    (*normalized_statuses, safe_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM nas_import_tasks
                    ORDER BY updated_at_ms DESC
                    LIMIT ?
                    """,
                    (safe_limit,),
                ).fetchall()
        finally:
            conn.close()
        return [self._from_row(row) for row in rows or []]

    def get_task(self, task_id: str) -> NasImportTask | None:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM nas_import_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                return None
            return self._from_row(row)
        finally:
            conn.close()

    def summary_metrics(self) -> dict[str, Any]:
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_tasks,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_tasks,
                    SUM(CASE WHEN status IN ('pending', 'running', 'canceling', 'pausing') THEN 1 ELSE 0 END) AS backlog_tasks,
                    AVG(
                        CASE WHEN status IN ('completed', 'failed', 'canceled')
                        THEN (updated_at_ms - created_at_ms)
                        ELSE NULL END
                    ) AS avg_duration_ms
                FROM nas_import_tasks
                """
            ).fetchone()
            status_rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM nas_import_tasks GROUP BY status"
            ).fetchall()
        finally:
            conn.close()

        status_counts: dict[str, int] = {}
        for item in status_rows or []:
            status_counts[str(item["status"] or "unknown")] = int(item["count"] or 0)

        return {
            "total_tasks": int((row["total_tasks"] if row is not None else 0) or 0),
            "failed_tasks": int((row["failed_tasks"] if row is not None else 0) or 0),
            "backlog_tasks": int((row["backlog_tasks"] if row is not None else 0) or 0),
            "avg_duration_ms": int(float((row["avg_duration_ms"] if row is not None else 0) or 0)),
            "status_counts": status_counts,
        }

    def update_task(self, task_id: str, **updates) -> NasImportTask | None:
        if not updates:
            return self.get_task(task_id)

        update_map = dict(updates)
        if "imported" in update_map:
            update_map["imported_json"] = self._encode_json(update_map.pop("imported"))
        if "skipped" in update_map:
            update_map["skipped_json"] = self._encode_json(update_map.pop("skipped"))
        if "failed" in update_map:
            update_map["failed_json"] = self._encode_json(update_map.pop("failed"))
        if "pending_files" in update_map:
            update_map["pending_files_json"] = self._encode_path_list(update_map.pop("pending_files"))
        update_map["updated_at_ms"] = int(time.time() * 1000)

        set_clause = ", ".join(f"{key} = ?" for key in update_map.keys())
        params = [update_map[key] for key in update_map.keys()]
        params.append(task_id)

        conn = self._conn()
        try:
            conn.execute(
                f"UPDATE nas_import_tasks SET {set_clause} WHERE task_id = ?",
                params,
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_task(task_id)

    def request_cancel_task(self, task_id: str) -> NasImportTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        if task.status in ("completed", "failed", "canceled"):
            return task
        now_ms = int(time.time() * 1000)
        if task.status in ("pending", "paused"):
            status = "canceled"
        elif task.status in ("running", "canceling", "pausing"):
            status = "canceling"
        else:
            status = task.status
        return self.update_task(task_id, status=status, cancel_requested_at_ms=now_ms)

    def clear_cancel_request(self, task_id: str) -> NasImportTask | None:
        return self.update_task(task_id, cancel_requested_at_ms=None)

    def request_pause_task(self, task_id: str) -> NasImportTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        if task.status in ("completed", "failed", "canceled"):
            return task
        if task.status == "pending":
            return self.update_task(task_id, status="paused")
        if task.status in ("running", "pausing"):
            return self.update_task(task_id, status="pausing")
        return task

    def request_resume_task(self, task_id: str) -> NasImportTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        if task.status == "paused":
            return self.update_task(task_id, status="pending")
        if task.status == "pausing":
            return self.update_task(task_id, status="running")
        return task

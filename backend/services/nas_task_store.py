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
    retry_count: int
    cancel_requested_at_ms: int | None
    created_at_ms: int
    updated_at_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "folder_path": self.folder_path,
            "kb_ref": self.kb_ref,
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
        retry_count: int = 0,
        cancel_requested_at_ms: int | None = None,
    ) -> NasImportTask:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO nas_import_tasks (
                    task_id, folder_path, kb_ref, total_files, processed_files,
                    imported_count, skipped_count, failed_count, status,
                    current_file, error, imported_json, skipped_json, failed_json, pending_files_json,
                    retry_count, cancel_requested_at_ms,
                    created_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    folder_path,
                    kb_ref,
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
        if task.status == "pending":
            status = "canceled"
        elif task.status in ("running", "canceling"):
            status = "canceling"
        else:
            status = task.status
        return self.update_task(task_id, status=status, cancel_requested_at_ms=now_ms)

    def clear_cancel_request(self, task_id: str) -> NasImportTask | None:
        return self.update_task(task_id, cancel_requested_at_ms=None)

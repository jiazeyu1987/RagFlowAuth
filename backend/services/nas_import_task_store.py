from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


class NasImportTaskStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    def _conn(self):
        return connect_sqlite(self.db_path)

    def _ensure_table(self) -> None:
        conn = self._conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nas_import_tasks (
                    task_id TEXT PRIMARY KEY,
                    folder_path TEXT NOT NULL,
                    kb_ref TEXT NOT NULL,
                    total_files INTEGER NOT NULL DEFAULT 0,
                    processed_files INTEGER NOT NULL DEFAULT 0,
                    imported_count INTEGER NOT NULL DEFAULT 0,
                    skipped_count INTEGER NOT NULL DEFAULT 0,
                    failed_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    current_file TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    imported_json TEXT NOT NULL DEFAULT '[]',
                    skipped_json TEXT NOT NULL DEFAULT '[]',
                    failed_json TEXT NOT NULL DEFAULT '[]',
                    created_at_ms INTEGER NOT NULL,
                    updated_at_ms INTEGER NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nas_import_tasks_updated ON nas_import_tasks(updated_at_ms)")
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _dump_list(value: list[dict[str, Any]] | None) -> str:
        safe = value if isinstance(value, list) else []
        return json.dumps(safe, ensure_ascii=False)

    @staticmethod
    def _load_list(value: Any) -> list[dict[str, Any]]:
        raw = str(value or "").strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except Exception:
            return []
        if not isinstance(parsed, list):
            return []
        return [x for x in parsed if isinstance(x, dict)]

    def create_task(
        self,
        *,
        task_id: str,
        folder_path: str,
        kb_ref: str,
        total_files: int,
        skipped_count: int = 0,
        skipped: list[dict[str, Any]] | None = None,
        status: str = "pending",
    ) -> None:
        now_ms = self._now_ms()
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO nas_import_tasks (
                    task_id, folder_path, kb_ref, total_files,
                    processed_files, imported_count, skipped_count, failed_count,
                    status, current_file, error,
                    imported_json, skipped_json, failed_json,
                    created_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(task_id or "").strip(),
                    str(folder_path or "").strip(),
                    str(kb_ref or "").strip(),
                    int(max(0, total_files)),
                    0,
                    0,
                    int(max(0, skipped_count)),
                    0,
                    str(status or "pending"),
                    "",
                    "",
                    "[]",
                    self._dump_list((skipped or [])[:50]),
                    "[]",
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM nas_import_tasks WHERE task_id = ?", (str(task_id or "").strip(),)).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        return self._row_to_payload(row)

    def mark_running(self, task_id: str) -> None:
        self._update_fields(task_id, {"status": "running"})

    def set_current_file(self, task_id: str, current_file: str) -> None:
        self._update_fields(task_id, {"current_file": str(current_file or "")})

    def mark_completed(self, task_id: str) -> None:
        self._update_fields(task_id, {"status": "completed", "current_file": ""})

    def mark_failed(self, task_id: str, error: str) -> None:
        self._update_fields(task_id, {"status": "failed", "error": str(error or ""), "current_file": ""})

    def _update_fields(self, task_id: str, fields: dict[str, Any]) -> None:
        payload = dict(fields or {})
        if not payload:
            return
        payload["updated_at_ms"] = self._now_ms()
        sets = ", ".join([f"{k} = ?" for k in payload.keys()])
        values = list(payload.values()) + [str(task_id or "").strip()]
        conn = self._conn()
        try:
            conn.execute(f"UPDATE nas_import_tasks SET {sets} WHERE task_id = ?", values)
            conn.commit()
        finally:
            conn.close()

    def apply_outcome(self, task_id: str, *, status: str, payload: dict[str, Any]) -> None:
        task_key = str(task_id or "").strip()
        outcome_status = str(status or "").strip()
        entry = payload if isinstance(payload, dict) else {}
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM nas_import_tasks WHERE task_id = ?", (task_key,)).fetchone()
            if not row:
                conn.rollback()
                return

            processed_files = int(row["processed_files"] or 0) + 1
            imported_count = int(row["imported_count"] or 0)
            skipped_count = int(row["skipped_count"] or 0)
            failed_count = int(row["failed_count"] or 0)

            imported = self._load_list(row["imported_json"])
            skipped = self._load_list(row["skipped_json"])
            failed = self._load_list(row["failed_json"])

            if outcome_status == "imported":
                imported_count += 1
                if len(imported) < 50:
                    imported.append(entry)
            elif outcome_status == "skipped":
                skipped_count += 1
                if len(skipped) < 50:
                    skipped.append(entry)
            else:
                failed_count += 1
                if len(failed) < 50:
                    failed.append(entry)

            conn.execute(
                """
                UPDATE nas_import_tasks
                SET processed_files = ?,
                    imported_count = ?,
                    skipped_count = ?,
                    failed_count = ?,
                    current_file = '',
                    imported_json = ?,
                    skipped_json = ?,
                    failed_json = ?,
                    updated_at_ms = ?
                WHERE task_id = ?
                """,
                (
                    processed_files,
                    imported_count,
                    skipped_count,
                    failed_count,
                    self._dump_list(imported),
                    self._dump_list(skipped),
                    self._dump_list(failed),
                    self._now_ms(),
                    task_key,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_payload(self, row) -> dict[str, Any]:
        total_files = int(row["total_files"] or 0)
        processed_files = int(row["processed_files"] or 0)
        progress_percent = 100 if total_files == 0 else int((processed_files / total_files) * 100)
        return {
            "task_id": str(row["task_id"] or ""),
            "folder_path": str(row["folder_path"] or ""),
            "kb_ref": str(row["kb_ref"] or ""),
            "total_files": total_files,
            "processed_files": processed_files,
            "imported_count": int(row["imported_count"] or 0),
            "skipped_count": int(row["skipped_count"] or 0),
            "failed_count": int(row["failed_count"] or 0),
            "status": str(row["status"] or ""),
            "current_file": str(row["current_file"] or ""),
            "error": str(row["error"] or ""),
            "imported": self._load_list(row["imported_json"]),
            "skipped": self._load_list(row["skipped_json"]),
            "failed": self._load_list(row["failed_json"]),
            "progress_percent": progress_percent,
            "remaining_files": max(total_files - processed_files, 0),
        }

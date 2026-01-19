import sqlite3
import time
import logging
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass
class DeletionLog:
    id: int
    doc_id: str
    filename: str
    kb_id: str
    deleted_by: str
    deleted_at_ms: int
    original_uploader: Optional[str] = None
    original_reviewer: Optional[str] = None
    ragflow_doc_id: Optional[str] = None
    kb_dataset_id: Optional[str] = None
    kb_name: Optional[str] = None
    action: Optional[str] = None
    ragflow_deleted: Optional[int] = None
    ragflow_delete_error: Optional[str] = None


class DeletionLogStore:
    def __init__(self, db_path: str = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger(__name__)

    def _get_connection(self):
        return connect_sqlite(self.db_path)

    def log_deletion(
        self,
        doc_id: str,
        filename: str,
        kb_id: str,
        deleted_by: str,
        kb_dataset_id: Optional[str] = None,
        kb_name: Optional[str] = None,
        original_uploader: Optional[str] = None,
        original_reviewer: Optional[str] = None,
        ragflow_doc_id: Optional[str] = None,
        *,
        action: str | None = None,
        ragflow_deleted: int | None = None,
        ragflow_delete_error: str | None = None,
    ) -> DeletionLog:
        """记录文件删除操作"""
        now_ms = int(time.time() * 1000)

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO deletion_logs (
                    doc_id, filename, kb_id, deleted_by, deleted_at_ms,
                    original_uploader, original_reviewer, ragflow_doc_id,
                    kb_dataset_id, kb_name, action, ragflow_deleted, ragflow_delete_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (doc_id, filename, kb_id, deleted_by, now_ms,
                  original_uploader, original_reviewer, ragflow_doc_id,
                  kb_dataset_id, (kb_name or kb_id), action, ragflow_deleted, ragflow_delete_error))
            conn.commit()

            # 获取插入的记录
            cursor.execute("SELECT last_insert_rowid()")
            log_id = cursor.fetchone()[0]

            self._logger.info(
                "[DELETE] deletion logged doc_id=%s filename=%s kb_id=%s deleted_by=%s",
                doc_id,
                filename,
                kb_id,
                deleted_by,
            )

            return DeletionLog(
                id=log_id,
                doc_id=doc_id,
                filename=filename,
                kb_id=kb_id,
                deleted_by=deleted_by,
                deleted_at_ms=now_ms,
                original_uploader=original_uploader,
                original_reviewer=original_reviewer,
                ragflow_doc_id=ragflow_doc_id,
                kb_dataset_id=kb_dataset_id,
                kb_name=(kb_name or kb_id),
                action=action,
                ragflow_deleted=ragflow_deleted,
                ragflow_delete_error=ragflow_delete_error,
            )
        finally:
            conn.close()

    def list_deletions(
        self,
        kb_id: Optional[str] = None,
        kb_refs: Optional[List[str]] = None,
        deleted_by: Optional[str] = None,
        limit: int = 100
    ) -> List[DeletionLog]:
        """获取删除记录列表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT id, doc_id, filename, kb_id, deleted_by, deleted_at_ms,
                       original_uploader, original_reviewer, ragflow_doc_id,
                       kb_dataset_id, kb_name, action, ragflow_deleted, ragflow_delete_error
                FROM deletion_logs
                WHERE 1=1
            """
            params = []

            refs = kb_refs or ([kb_id] if kb_id else [])
            if refs:
                placeholders = ",".join("?" for _ in refs)
                query += f" AND (kb_id IN ({placeholders}) OR kb_dataset_id IN ({placeholders}) OR kb_name IN ({placeholders}))"
                params.extend(list(refs))
                params.extend(list(refs))
                params.extend(list(refs))

            if deleted_by:
                query += " AND deleted_by = ?"
                params.append(deleted_by)

            query += " ORDER BY deleted_at_ms DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [DeletionLog(*row) for row in rows]
        finally:
            conn.close()



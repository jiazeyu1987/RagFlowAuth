import sqlite3
import time
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite



@dataclass
class DownloadLog:
    id: int
    doc_id: str
    filename: str
    kb_id: str
    downloaded_by: str
    downloaded_at_ms: int
    ragflow_doc_id: Optional[str] = None
    is_batch: bool = False
    kb_dataset_id: Optional[str] = None
    kb_name: Optional[str] = None


class DownloadLogStore:
    def __init__(self, db_path: str = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        return connect_sqlite(self.db_path)

    def log_download(
        self,
        doc_id: str,
        filename: str,
        kb_id: str,
        downloaded_by: str,
        ragflow_doc_id: Optional[str] = None,
        is_batch: bool = False,
        kb_dataset_id: Optional[str] = None,
        kb_name: Optional[str] = None
    ) -> DownloadLog:
        """记录文件下载操作"""
        now_ms = int(time.time() * 1000)

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO download_logs (
                    doc_id, filename, kb_id, downloaded_by, downloaded_at_ms,
                    ragflow_doc_id, is_batch, kb_dataset_id, kb_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (doc_id, filename, kb_id, downloaded_by, now_ms,
                  ragflow_doc_id, 1 if is_batch else 0, kb_dataset_id, (kb_name or kb_id)))
            conn.commit()

            # 获取插入的记录
            cursor.execute("SELECT last_insert_rowid()")
            log_id = cursor.fetchone()[0]

            return DownloadLog(
                id=log_id,
                doc_id=doc_id,
                filename=filename,
                kb_id=kb_id,
                downloaded_by=downloaded_by,
                downloaded_at_ms=now_ms,
                ragflow_doc_id=ragflow_doc_id,
                is_batch=is_batch,
                kb_dataset_id=kb_dataset_id,
                kb_name=(kb_name or kb_id),
            )
        finally:
            conn.close()

    def list_downloads(
        self,
        kb_id: Optional[str] = None,
        kb_refs: Optional[List[str]] = None,
        downloaded_by: Optional[str] = None,
        limit: int = 100
    ) -> List[DownloadLog]:
        """获取下载记录列表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT id, doc_id, filename, kb_id, downloaded_by, downloaded_at_ms,
                       ragflow_doc_id, is_batch, kb_dataset_id, kb_name
                FROM download_logs
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

            if downloaded_by:
                query += " AND downloaded_by = ?"
                params.append(downloaded_by)

            query += " ORDER BY downloaded_at_ms DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [DownloadLog(*row) for row in rows]
        finally:
            conn.close()

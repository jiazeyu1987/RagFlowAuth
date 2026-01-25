from __future__ import annotations

import logging
import time
import uuid
from typing import List, Optional

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

from .models import KbDocument

logger = logging.getLogger(__name__)


class KbStore:
    def __init__(self, db_path: str = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        return connect_sqlite(self.db_path)

    def create_document(
        self,
        filename: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        uploaded_by: str,
        kb_id: str = "灞曞巺",
        kb_dataset_id: Optional[str] = None,
        kb_name: Optional[str] = None,
        status: str = "pending",
    ) -> KbDocument:
        doc_id = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)

        logger.debug(
            "[KbStore] create_document filename=%s uploaded_by=%s kb_id=%s status=%s",
            filename,
            uploaded_by,
            kb_id,
            status,
        )

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO kb_documents (
                    doc_id, filename, file_path, file_size, mime_type,
                    uploaded_by, status, uploaded_at_ms, kb_id, kb_dataset_id, kb_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    filename,
                    file_path,
                    file_size,
                    mime_type,
                    uploaded_by,
                    status,
                    now_ms,
                    kb_id,
                    kb_dataset_id,
                    (kb_name or kb_id),
                ),
            )
            conn.commit()

            return KbDocument(
                doc_id=doc_id,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                uploaded_by=uploaded_by,
                status=status,
                uploaded_at_ms=now_ms,
                kb_id=kb_id,
                kb_dataset_id=kb_dataset_id,
                kb_name=(kb_name or kb_id),
            )
        finally:
            conn.close()

    def get_document(self, doc_id: str) -> Optional[KbDocument]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT doc_id, filename, file_path, file_size, mime_type,
                       uploaded_by, status, uploaded_at_ms, reviewed_by,
                       reviewed_at_ms, review_notes, ragflow_doc_id, kb_id, kb_dataset_id, kb_name
                FROM kb_documents WHERE doc_id = ?
                """,
                (doc_id,),
            )
            row = cursor.fetchone()
            if row:
                return KbDocument(*row)
            return None
        finally:
            conn.close()

    def get_document_by_ragflow_id(
        self,
        ragflow_doc_id: str,
        kb_id: str = "灞曞巺",
        kb_refs: Optional[List[str]] = None,
    ) -> Optional[KbDocument]:
        """閫氳繃RAGFlow鐨刣oc_id鏌ユ壘鏈湴鏂囨。璁板綍"""
        refs = kb_refs or ([kb_id] if kb_id else [])
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if refs:
                placeholders = ",".join("?" for _ in refs)
                cursor.execute(
                    f"""
                    SELECT doc_id, filename, file_path, file_size, mime_type,
                           uploaded_by, status, uploaded_at_ms, reviewed_by,
                           reviewed_at_ms, review_notes, ragflow_doc_id, kb_id, kb_dataset_id, kb_name
                    FROM kb_documents
                    WHERE ragflow_doc_id = ?
                      AND (kb_id IN ({placeholders}) OR kb_dataset_id IN ({placeholders}) OR kb_name IN ({placeholders}))
                    """,
                    [ragflow_doc_id, *refs, *refs, *refs],
                )
            else:
                cursor.execute(
                    """
                    SELECT doc_id, filename, file_path, file_size, mime_type,
                           uploaded_by, status, uploaded_at_ms, reviewed_by,
                           reviewed_at_ms, review_notes, ragflow_doc_id, kb_id, kb_dataset_id, kb_name
                    FROM kb_documents
                    WHERE ragflow_doc_id = ?
                    """,
                    (ragflow_doc_id,),
                )
            row = cursor.fetchone()
            if row:
                return KbDocument(*row)
            return None
        finally:
            conn.close()

    def list_documents(
        self,
        status: Optional[str] = None,
        kb_id: Optional[str] = None,
        kb_refs: Optional[List[str]] = None,
        uploaded_by: Optional[str] = None,
        limit: int = 100,
    ) -> List[KbDocument]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT doc_id, filename, file_path, file_size, mime_type,
                       uploaded_by, status, uploaded_at_ms, reviewed_by,
                       reviewed_at_ms, review_notes, ragflow_doc_id, kb_id, kb_dataset_id, kb_name
                FROM kb_documents
                WHERE 1=1
            """
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)
            refs = kb_refs or ([kb_id] if kb_id else [])
            if refs:
                placeholders = ",".join("?" for _ in refs)
                query += (
                    f" AND (kb_id IN ({placeholders}) OR kb_dataset_id IN ({placeholders}) OR kb_name IN ({placeholders}))"
                )
                params.extend(list(refs))
                params.extend(list(refs))
                params.extend(list(refs))
            if uploaded_by:
                query += " AND uploaded_by = ?"
                params.append(uploaded_by)

            query += " ORDER BY uploaded_at_ms DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [KbDocument(*row) for row in rows]
        finally:
            conn.close()

    def update_document_status(
        self,
        doc_id: str,
        status: str,
        reviewed_by: Optional[str] = None,
        review_notes: Optional[str] = None,
        ragflow_doc_id: Optional[str] = None,
    ) -> Optional[KbDocument]:
        now_ms = int(time.time() * 1000)

        logger.debug(
            "[KbStore] update_document_status doc_id=%s status=%s reviewed_by=%s",
            doc_id,
            status,
            reviewed_by,
        )

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE kb_documents
                SET status = ?, reviewed_by = ?, reviewed_at_ms = ?, review_notes = ?, ragflow_doc_id = ?
                WHERE doc_id = ?
                """,
                (status, reviewed_by, now_ms, review_notes, ragflow_doc_id, doc_id),
            )
            conn.commit()

            return self.get_document(doc_id)
        finally:
            conn.close()

    def delete_document(self, doc_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM kb_documents WHERE doc_id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def count_documents(
        self,
        status: Optional[str] = None,
        kb_id: Optional[str] = None,
        kb_ids: Optional[List[str]] = None,
        kb_refs: Optional[List[str]] = None,
        uploaded_by: Optional[str] = None,
    ) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT COUNT(*) FROM kb_documents WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            refs = kb_refs or (list(kb_ids) if kb_ids else ([kb_id] if kb_id else []))
            if refs:
                placeholders = ",".join("?" for _ in refs)
                query += (
                    f" AND (kb_id IN ({placeholders}) OR kb_dataset_id IN ({placeholders}) OR kb_name IN ({placeholders}))"
                )
                params.extend(list(refs))
                params.extend(list(refs))
                params.extend(list(refs))
            if uploaded_by:
                query += " AND uploaded_by = ?"
                params.append(uploaded_by)

            cursor.execute(query, params)
            return cursor.fetchone()[0]
        finally:
            conn.close()


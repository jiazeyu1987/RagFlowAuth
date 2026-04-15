from __future__ import annotations

import hashlib
import logging
import time
import uuid
from pathlib import Path
from typing import List, Optional

from backend.app.core.managed_paths import (
    resolve_managed_data_storage_path,
    to_managed_data_storage_path,
)
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

    @staticmethod
    def _document_select_clause() -> str:
        return """
            doc_id,
            filename,
            file_path,
            file_size,
            mime_type,
            uploaded_by,
            status,
            uploaded_at_ms,
            reviewed_by,
            reviewed_at_ms,
            review_notes,
            ragflow_doc_id,
            kb_id,
            kb_dataset_id,
            kb_name,
            logical_doc_id,
            version_no,
            previous_doc_id,
            superseded_by_doc_id,
            is_current,
            effective_status,
            archived_at_ms,
            retention_until_ms,
            file_sha256,
            retired_by,
            retirement_reason,
            archive_manifest_path,
            archive_package_path,
            archive_package_sha256
        """

    @staticmethod
    def _effective_status_for(status: str) -> str:
        return str(status or "").strip() or "pending"

    @staticmethod
    def _row_to_document(row) -> Optional[KbDocument]:
        if not row:
            return None
        file_path = resolve_managed_data_storage_path(
            str(row["file_path"] or ""),
            field_name="kb_documents.file_path",
        )
        archive_manifest_path = (
            resolve_managed_data_storage_path(
                str(row["archive_manifest_path"] or ""),
                field_name="kb_documents.archive_manifest_path",
            )
            if row["archive_manifest_path"]
            else None
        )
        archive_package_path = (
            resolve_managed_data_storage_path(
                str(row["archive_package_path"] or ""),
                field_name="kb_documents.archive_package_path",
            )
            if row["archive_package_path"]
            else None
        )
        return KbDocument(
            doc_id=str(row["doc_id"]),
            filename=str(row["filename"]),
            file_path=str(file_path),
            file_size=int(row["file_size"] or 0),
            mime_type=str(row["mime_type"]),
            uploaded_by=str(row["uploaded_by"]),
            status=str(row["status"]),
            uploaded_at_ms=int(row["uploaded_at_ms"] or 0),
            reviewed_by=(str(row["reviewed_by"]) if row["reviewed_by"] else None),
            reviewed_at_ms=(int(row["reviewed_at_ms"]) if row["reviewed_at_ms"] is not None else None),
            review_notes=row["review_notes"],
            ragflow_doc_id=(str(row["ragflow_doc_id"]) if row["ragflow_doc_id"] else None),
            kb_id=str(row["kb_id"]),
            kb_dataset_id=(str(row["kb_dataset_id"]) if row["kb_dataset_id"] else None),
            kb_name=(str(row["kb_name"]) if row["kb_name"] else None),
            logical_doc_id=(str(row["logical_doc_id"]) if row["logical_doc_id"] else None),
            version_no=int(row["version_no"] or 1),
            previous_doc_id=(str(row["previous_doc_id"]) if row["previous_doc_id"] else None),
            superseded_by_doc_id=(str(row["superseded_by_doc_id"]) if row["superseded_by_doc_id"] else None),
            is_current=bool(row["is_current"]) if row["is_current"] is not None else True,
            effective_status=(str(row["effective_status"]) if row["effective_status"] else None),
            archived_at_ms=(int(row["archived_at_ms"]) if row["archived_at_ms"] is not None else None),
            retention_until_ms=(int(row["retention_until_ms"]) if row["retention_until_ms"] is not None else None),
            file_sha256=(str(row["file_sha256"]) if row["file_sha256"] else None),
            retired_by=(str(row["retired_by"]) if row["retired_by"] else None),
            retirement_reason=(str(row["retirement_reason"]) if row["retirement_reason"] else None),
            archive_manifest_path=(str(archive_manifest_path) if archive_manifest_path else None),
            archive_package_path=(str(archive_package_path) if archive_package_path else None),
            archive_package_sha256=(str(row["archive_package_sha256"]) if row["archive_package_sha256"] else None),
        )

    @staticmethod
    def _calculate_file_sha256(file_path: str | Path) -> str:
        digest = hashlib.sha256()
        with Path(file_path).open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def create_document(
        self,
        filename: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        uploaded_by: str,
        kb_id: str = "展厅",
        kb_dataset_id: Optional[str] = None,
        kb_name: Optional[str] = None,
        status: str = "pending",
        logical_doc_id: Optional[str] = None,
        version_no: int = 1,
        previous_doc_id: Optional[str] = None,
        superseded_by_doc_id: Optional[str] = None,
        is_current: bool = True,
        effective_status: Optional[str] = None,
        archived_at_ms: Optional[int] = None,
        retention_until_ms: Optional[int] = None,
    ) -> KbDocument:
        doc_id = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)
        logical_doc_id = str(logical_doc_id or doc_id)
        version_no = max(1, int(version_no or 1))
        stored_file_path = to_managed_data_storage_path(
            file_path,
            field_name="kb_documents.file_path",
        )
        resolved_file_path = resolve_managed_data_storage_path(
            stored_file_path,
            field_name="kb_documents.file_path",
        )
        file_sha256 = self._calculate_file_sha256(resolved_file_path)
        effective_status = str(effective_status or self._effective_status_for(status))

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
                    uploaded_by, status, uploaded_at_ms, kb_id, kb_dataset_id, kb_name,
                    logical_doc_id, version_no, previous_doc_id, superseded_by_doc_id,
                    is_current, effective_status, archived_at_ms, retention_until_ms, file_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    filename,
                    stored_file_path,
                    file_size,
                    mime_type,
                    uploaded_by,
                    status,
                    now_ms,
                    kb_id,
                    kb_dataset_id,
                    (kb_name or kb_id),
                    logical_doc_id,
                    version_no,
                    previous_doc_id,
                    superseded_by_doc_id,
                    1 if is_current else 0,
                    effective_status,
                    archived_at_ms,
                    retention_until_ms,
                    file_sha256,
                ),
            )
            conn.commit()

            return KbDocument(
                doc_id=doc_id,
                filename=filename,
                file_path=str(resolved_file_path),
                file_size=file_size,
                mime_type=mime_type,
                uploaded_by=uploaded_by,
                status=status,
                uploaded_at_ms=now_ms,
                kb_id=kb_id,
                kb_dataset_id=kb_dataset_id,
                kb_name=(kb_name or kb_id),
                logical_doc_id=logical_doc_id,
                version_no=version_no,
                previous_doc_id=previous_doc_id,
                superseded_by_doc_id=superseded_by_doc_id,
                is_current=is_current,
                effective_status=effective_status,
                archived_at_ms=archived_at_ms,
                retention_until_ms=retention_until_ms,
                file_sha256=file_sha256,
            )
        finally:
            conn.close()

    def get_document(self, doc_id: str) -> Optional[KbDocument]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    """ + self._document_select_clause() + """
                FROM kb_documents WHERE doc_id = ?
                """,
                (doc_id,),
            )
            row = cursor.fetchone()
            return self._row_to_document(row)
        finally:
            conn.close()

    def get_document_by_ragflow_id(
        self,
        ragflow_doc_id: str,
        kb_id: str = "展厅",
        kb_refs: Optional[List[str]] = None,
    ) -> Optional[KbDocument]:
        """通过 RAGFlow 的 doc_id 查找本地文档记录"""
        refs = kb_refs or ([kb_id] if kb_id else [])
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if refs:
                placeholders = ",".join("?" for _ in refs)
                cursor.execute(
                    f"""
                    SELECT
                        {self._document_select_clause()}
                    FROM kb_documents
                    WHERE ragflow_doc_id = ?
                      AND (kb_id IN ({placeholders}) OR kb_dataset_id IN ({placeholders}) OR kb_name IN ({placeholders}))
                    """,
                    [ragflow_doc_id, *refs, *refs, *refs],
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        """ + self._document_select_clause() + """
                    FROM kb_documents
                    WHERE ragflow_doc_id = ?
                    """,
                    (ragflow_doc_id,),
                )
            row = cursor.fetchone()
            return self._row_to_document(row)
        finally:
            conn.close()

    def list_documents(
        self,
        status: Optional[str] = None,
        kb_id: Optional[str] = None,
        kb_refs: Optional[List[str]] = None,
        uploaded_by: Optional[str] = None,
        limit: int = 100,
        include_history: bool = False,
        effective_status: Optional[str] = None,
    ) -> List[KbDocument]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT
                    """ + self._document_select_clause() + """
                FROM kb_documents
                WHERE 1=1
            """
            params = []

            if not include_history:
                query += " AND is_current = 1"
            if status:
                query += " AND status = ?"
                params.append(status)
            if effective_status:
                query += " AND effective_status = ?"
                params.append(str(effective_status))
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
            return [self._row_to_document(row) for row in rows if row]
        finally:
            conn.close()

    def list_retired_documents(
        self,
        *,
        kb_id: Optional[str] = None,
        kb_refs: Optional[List[str]] = None,
        uploaded_by: Optional[str] = None,
        limit: int = 100,
        include_expired: bool = False,
        now_ms: Optional[int] = None,
    ) -> List[KbDocument]:
        current_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT
                    """ + self._document_select_clause() + """
                FROM kb_documents
                WHERE effective_status = 'archived'
            """
            params = []
            if not include_expired:
                query += " AND (retention_until_ms IS NULL OR retention_until_ms >= ?)"
                params.append(current_ms)
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
            query += " ORDER BY archived_at_ms DESC, uploaded_at_ms DESC LIMIT ?"
            params.append(int(max(1, min(500, limit))))
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_document(row) for row in rows if row]
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
                SET status = ?,
                    reviewed_by = ?,
                    reviewed_at_ms = ?,
                    review_notes = ?,
                    ragflow_doc_id = ?,
                    effective_status = CASE
                        WHEN effective_status IN ('superseded', 'archived') THEN effective_status
                        ELSE ?
                    END
                WHERE doc_id = ?
                """,
                (
                    status,
                    reviewed_by,
                    now_ms,
                    review_notes,
                    ragflow_doc_id,
                    self._effective_status_for(status),
                    doc_id,
                ),
            )
            conn.commit()

            return self.get_document(doc_id)
        finally:
            conn.close()

    def promote_new_version(
        self,
        *,
        doc_id: str,
        previous_doc_id: str,
        logical_doc_id: str,
        version_no: int,
        effective_status: Optional[str] = None,
        retention_until_ms: Optional[int] = None,
    ) -> Optional[KbDocument]:
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE kb_documents
                SET logical_doc_id = ?,
                    version_no = ?,
                    previous_doc_id = ?,
                    superseded_by_doc_id = NULL,
                    is_current = 1,
                    effective_status = ?,
                    archived_at_ms = NULL,
                    retention_until_ms = ?,
                    reviewed_at_ms = reviewed_at_ms
                WHERE doc_id = ?
                """,
                (
                    str(logical_doc_id),
                    max(1, int(version_no or 1)),
                    str(previous_doc_id),
                    str(effective_status or "approved"),
                    retention_until_ms,
                    str(doc_id),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_document(doc_id)

    def mark_superseded(
        self,
        *,
        doc_id: str,
        superseded_by_doc_id: str,
        retention_until_ms: Optional[int] = None,
    ) -> Optional[KbDocument]:
        now_ms = int(time.time() * 1000)
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE kb_documents
                SET superseded_by_doc_id = ?,
                    is_current = 0,
                    effective_status = 'superseded',
                    archived_at_ms = ?,
                    retention_until_ms = COALESCE(?, retention_until_ms)
                WHERE doc_id = ?
                """,
                (
                    str(superseded_by_doc_id),
                    now_ms,
                    retention_until_ms,
                    str(doc_id),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_document(doc_id)

    def apply_version_replacement(
        self,
        *,
        old_doc_id: str,
        new_doc_id: str,
        effective_status: str = "approved",
        retention_until_ms: Optional[int] = None,
    ) -> tuple[Optional[KbDocument], Optional[KbDocument]]:
        now_ms = int(time.time() * 1000)
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            old_row = conn.execute(
                """
                SELECT logical_doc_id, version_no, retention_until_ms
                FROM kb_documents
                WHERE doc_id = ?
                """,
                (str(old_doc_id),),
            ).fetchone()
            if not old_row:
                raise KeyError(f"document not found: {old_doc_id}")

            new_row = conn.execute(
                "SELECT doc_id FROM kb_documents WHERE doc_id = ?",
                (str(new_doc_id),),
            ).fetchone()
            if not new_row:
                raise KeyError(f"document not found: {new_doc_id}")

            logical_doc_id = str(old_row["logical_doc_id"] or old_doc_id)
            next_version_no = max(1, int(old_row["version_no"] or 1)) + 1
            next_retention_until_ms = (
                retention_until_ms if retention_until_ms is not None else old_row["retention_until_ms"]
            )

            conn.execute(
                """
                UPDATE kb_documents
                SET superseded_by_doc_id = ?,
                    is_current = 0,
                    effective_status = 'superseded',
                    archived_at_ms = ?,
                    retention_until_ms = COALESCE(?, retention_until_ms)
                WHERE doc_id = ?
                """,
                (
                    str(new_doc_id),
                    now_ms,
                    next_retention_until_ms,
                    str(old_doc_id),
                ),
            )
            conn.execute(
                """
                UPDATE kb_documents
                SET logical_doc_id = ?,
                    version_no = ?,
                    previous_doc_id = ?,
                    superseded_by_doc_id = NULL,
                    is_current = 1,
                    effective_status = ?,
                    archived_at_ms = NULL,
                    retention_until_ms = ?
                WHERE doc_id = ?
                """,
                (
                    logical_doc_id,
                    next_version_no,
                    str(old_doc_id),
                    str(effective_status or "approved"),
                    next_retention_until_ms,
                    str(new_doc_id),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_document(old_doc_id), self.get_document(new_doc_id)

    def retire_document(
        self,
        *,
        doc_id: str,
        archived_file_path: str,
        archive_manifest_path: str,
        archive_package_path: str,
        archive_package_sha256: str,
        retired_by: str,
        retirement_reason: str,
        retention_until_ms: int,
        archived_at_ms: Optional[int] = None,
        conn=None,
    ) -> Optional[KbDocument]:
        archived_at_ms = int(time.time() * 1000) if archived_at_ms is None else int(archived_at_ms)
        retired_by = str(retired_by or "").strip()
        retirement_reason = str(retirement_reason or "").strip()
        archived_file_path = str(archived_file_path or "").strip()
        archive_manifest_path = str(archive_manifest_path or "").strip()
        archive_package_path = str(archive_package_path or "").strip()
        archive_package_sha256 = str(archive_package_sha256 or "").strip()
        retention_until_ms = int(retention_until_ms)

        if not retired_by:
            raise ValueError("retired_by_required")
        if not retirement_reason:
            raise ValueError("retirement_reason_required")
        if not archived_file_path:
            raise ValueError("archived_file_path_required")
        if not archive_manifest_path:
            raise ValueError("archive_manifest_path_required")
        if not archive_package_path:
            raise ValueError("archive_package_path_required")
        if not archive_package_sha256:
            raise ValueError("archive_package_sha256_required")

        stored_archived_file_path = to_managed_data_storage_path(
            archived_file_path,
            field_name="kb_documents.file_path",
        )
        stored_archive_manifest_path = to_managed_data_storage_path(
            archive_manifest_path,
            field_name="kb_documents.archive_manifest_path",
        )
        stored_archive_package_path = to_managed_data_storage_path(
            archive_package_path,
            field_name="kb_documents.archive_package_path",
        )

        owns_conn = False
        if conn is None:
            conn = self._get_connection()
            owns_conn = True
        try:
            conn.execute(
                """
                UPDATE kb_documents
                SET file_path = ?,
                    is_current = 0,
                    effective_status = 'archived',
                    archived_at_ms = ?,
                    retention_until_ms = ?,
                    retired_by = ?,
                    retirement_reason = ?,
                    archive_manifest_path = ?,
                    archive_package_path = ?,
                    archive_package_sha256 = ?
                WHERE doc_id = ?
                """,
                (
                    stored_archived_file_path,
                    archived_at_ms,
                    retention_until_ms,
                    retired_by,
                    retirement_reason,
                    stored_archive_manifest_path,
                    stored_archive_package_path,
                    archive_package_sha256,
                    str(doc_id),
                ),
            )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn:
                conn.close()
        return self.get_document(doc_id)

    def list_versions(self, doc_id_or_logical_doc_id: str, *, limit: int = 100) -> List[KbDocument]:
        ref = str(doc_id_or_logical_doc_id or "").strip()
        if not ref:
            return []
        current = self.get_document(ref)
        logical_doc_id = current.logical_doc_id if current and current.logical_doc_id else ref

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    """ + self._document_select_clause() + """
                FROM kb_documents
                WHERE logical_doc_id = ?
                ORDER BY version_no DESC, uploaded_at_ms DESC
                LIMIT ?
                """,
                (logical_doc_id, int(max(1, min(500, limit)))),
            )
            rows = cursor.fetchall()
            return [self._row_to_document(row) for row in rows if row]
        finally:
            conn.close()

    def get_current_document(self, doc_id_or_logical_doc_id: str) -> Optional[KbDocument]:
        ref = str(doc_id_or_logical_doc_id or "").strip()
        if not ref:
            return None
        current = self.get_document(ref)
        logical_doc_id = current.logical_doc_id if current and current.logical_doc_id else ref

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    """ + self._document_select_clause() + """
                FROM kb_documents
                WHERE logical_doc_id = ?
                  AND is_current = 1
                ORDER BY version_no DESC, uploaded_at_ms DESC
                LIMIT 1
                """,
                (logical_doc_id,),
            )
            row = cursor.fetchone()
            return self._row_to_document(row)
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

    def mark_document_destroyed(
        self,
        *,
        doc_id: str,
        destroyed_at_ms: Optional[int] = None,
    ) -> Optional[KbDocument]:
        now_ms = int(time.time() * 1000) if destroyed_at_ms is None else int(destroyed_at_ms)
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE kb_documents
                SET status = 'destroyed',
                    effective_status = 'destroyed',
                    reviewed_at_ms = COALESCE(reviewed_at_ms, ?),
                    archive_manifest_path = NULL,
                    archive_package_path = NULL,
                    archive_package_sha256 = NULL
                WHERE doc_id = ?
                """,
                (
                    now_ms,
                    str(doc_id),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_document(doc_id)

    def count_documents(
        self,
        status: Optional[str] = None,
        kb_id: Optional[str] = None,
        kb_ids: Optional[List[str]] = None,
        kb_refs: Optional[List[str]] = None,
        uploaded_by: Optional[str] = None,
        include_history: bool = False,
        effective_status: Optional[str] = None,
    ) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT COUNT(*) FROM kb_documents WHERE 1=1"
            params = []

            if not include_history:
                query += " AND is_current = 1"
            if status:
                query += " AND status = ?"
                params.append(status)
            if effective_status:
                query += " AND effective_status = ?"
                params.append(str(effective_status))

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


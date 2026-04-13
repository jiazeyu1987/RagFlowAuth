from __future__ import annotations

import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.core.config import settings
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.paths import resolve_repo_path
from backend.database.sqlite import connect_sqlite
from backend.services.audit_helpers import actor_fields_from_ctx
from backend.services.document_control.models import ControlledDocument, ControlledRevision
from backend.services.knowledge_ingestion import KnowledgeIngestionManager


ALLOWED_STATUSES = ("draft", "in_review", "approved", "effective", "obsolete")
ALLOWED_TRANSITIONS = {
    "draft": {"in_review"},
    "in_review": {"approved"},
    "approved": {"effective"},
    "effective": {"obsolete"},
}


@dataclass
class DocumentControlError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class DocumentControlService:
    def __init__(self, *, deps: Any):
        self._deps = deps
        kb_store = getattr(deps, "kb_store", None)
        db_path = str(getattr(kb_store, "db_path", "") or "").strip()
        if not db_path:
            raise DocumentControlError("document_control_db_path_missing", status_code=500)
        self._db_path = Path(db_path).resolve()

    @classmethod
    def from_deps(cls, deps: Any) -> "DocumentControlService":
        return cls(deps=deps)

    def _connect(self):
        return connect_sqlite(self._db_path)

    @staticmethod
    def _map_integrity_error(exc: sqlite3.IntegrityError) -> DocumentControlError:
        message = str(exc).lower()
        if "controlled_documents.doc_code" in message or "idx_controlled_documents_doc_code" in message:
            return DocumentControlError("doc_code_conflict", status_code=409)
        if "controlled_revisions.controlled_document_id, controlled_revisions.revision_no" in message:
            return DocumentControlError("revision_no_conflict", status_code=409)
        if "idx_controlled_revisions_doc_revision_no" in message:
            return DocumentControlError("revision_no_conflict", status_code=409)
        if "idx_controlled_revisions_one_effective" in message:
            return DocumentControlError("effective_revision_conflict", status_code=409)
        return DocumentControlError("document_control_conflict", status_code=409)

    @staticmethod
    def _require_text(value: str | None, code: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise DocumentControlError(code)
        return text

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _safe_segment(value: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in str(value or "").strip())
        return safe or "controlled_document"

    def _staged_file_path(self, *, doc_code: str, revision_no: int, upload_filename: str) -> tuple[str, Path]:
        display_name, relative_path = KnowledgeIngestionManager._normalize_relative_upload_path(upload_filename)
        root = resolve_repo_path(settings.UPLOAD_DIR) / "document_control" / self._safe_segment(doc_code) / f"v{revision_no:03d}"
        final_path = root / relative_path
        return display_name, final_path

    @staticmethod
    def _detect_mime(filename: str, content_type: str | None) -> str:
        return KnowledgeIngestionManager._detect_mime(filename, content_type)

    @staticmethod
    def _write_upload(*, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def _resolve_kb_info(self, target_kb_id: str) -> tuple[str, str | None, str | None]:
        kb_info = resolve_kb_ref(self._deps, target_kb_id)
        kb_id = str(kb_info.dataset_id or target_kb_id).strip()
        kb_dataset_id = str(kb_info.dataset_id).strip() if kb_info.dataset_id else None
        kb_name = str(kb_info.name).strip() if kb_info.name else str(target_kb_id).strip()
        return kb_id, kb_dataset_id, kb_name

    def _create_kb_document(
        self,
        *,
        controlled_document_id: str,
        revision_no: int,
        file_path: Path,
        filename: str,
        mime_type: str,
        uploaded_by: str,
        kb_id: str,
        kb_dataset_id: str | None,
        kb_name: str | None,
        previous_doc_id: str | None,
        is_current: bool,
        ):
        return self._deps.kb_store.create_document(
            filename=filename,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            mime_type=mime_type,
            uploaded_by=uploaded_by,
            kb_id=kb_id,
            kb_dataset_id=kb_dataset_id,
            kb_name=kb_name,
            status="draft",
            logical_doc_id=controlled_document_id,
            version_no=revision_no,
            previous_doc_id=previous_doc_id,
            is_current=is_current,
            effective_status="draft",
        )

    def _revision_from_joined_row(self, row) -> ControlledRevision:
        return ControlledRevision(
            controlled_revision_id=str(row["controlled_revision_id"]),
            controlled_document_id=str(row["controlled_document_id"]),
            kb_doc_id=str(row["kb_doc_id"]),
            revision_no=int(row["revision_no"]),
            status=str(row["status"]),
            change_summary=(str(row["change_summary"]) if row["change_summary"] else None),
            previous_revision_id=(str(row["previous_revision_id"]) if row["previous_revision_id"] else None),
            approved_by=(str(row["approved_by"]) if row["approved_by"] else None),
            approved_at_ms=(int(row["approved_at_ms"]) if row["approved_at_ms"] is not None else None),
            effective_at_ms=(int(row["effective_at_ms"]) if row["effective_at_ms"] is not None else None),
            obsolete_at_ms=(int(row["obsolete_at_ms"]) if row["obsolete_at_ms"] is not None else None),
            created_by=str(row["created_by"]),
            created_at_ms=int(row["created_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
            filename=str(row["filename"]),
            file_size=int(row["file_size"]),
            mime_type=str(row["mime_type"]),
            uploaded_by=str(row["uploaded_by"]),
            uploaded_at_ms=int(row["uploaded_at_ms"]),
            reviewed_by=(str(row["reviewed_by"]) if row["reviewed_by"] else None),
            reviewed_at_ms=(int(row["reviewed_at_ms"]) if row["reviewed_at_ms"] is not None else None),
            review_notes=(str(row["review_notes"]) if row["review_notes"] else None),
            ragflow_doc_id=(str(row["ragflow_doc_id"]) if row["ragflow_doc_id"] else None),
            kb_id=str(row["kb_id"]),
            kb_dataset_id=(str(row["kb_dataset_id"]) if row["kb_dataset_id"] else None),
            kb_name=(str(row["kb_name"]) if row["kb_name"] else None),
            file_sha256=(str(row["file_sha256"]) if row["file_sha256"] else None),
            file_path=str(row["file_path"]),
        )

    def _document_from_row(
        self,
        row,
        *,
        current_revision: ControlledRevision | None = None,
        effective_revision: ControlledRevision | None = None,
        revisions: list[ControlledRevision] | None = None,
    ) -> ControlledDocument:
        return ControlledDocument(
            controlled_document_id=str(row["controlled_document_id"]),
            doc_code=str(row["doc_code"]),
            title=str(row["title"]),
            document_type=str(row["document_type"]),
            product_name=(str(row["product_name"]) if row["product_name"] else None),
            registration_ref=(str(row["registration_ref"]) if row["registration_ref"] else None),
            target_kb_id=str(row["target_kb_id"]),
            target_kb_name=(str(row["target_kb_name"]) if row["target_kb_name"] else None),
            current_revision_id=(str(row["current_revision_id"]) if row["current_revision_id"] else None),
            effective_revision_id=(str(row["effective_revision_id"]) if row["effective_revision_id"] else None),
            created_by=str(row["created_by"]),
            created_at_ms=int(row["created_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
            current_revision=current_revision,
            effective_revision=effective_revision,
            revisions=revisions,
        )

    def _get_revision_rows(self, conn, *, controlled_document_id: str) -> list:
        return conn.execute(
            """
            SELECT
                r.controlled_revision_id,
                r.controlled_document_id,
                r.kb_doc_id,
                r.revision_no,
                r.status,
                r.change_summary,
                r.previous_revision_id,
                r.approved_by,
                r.approved_at_ms,
                r.effective_at_ms,
                r.obsolete_at_ms,
                r.created_by,
                r.created_at_ms,
                r.updated_at_ms,
                k.filename,
                k.file_size,
                k.mime_type,
                k.uploaded_by,
                k.uploaded_at_ms,
                k.reviewed_by,
                k.reviewed_at_ms,
                k.review_notes,
                k.ragflow_doc_id,
                k.kb_id,
                k.kb_dataset_id,
                k.kb_name,
                k.file_sha256,
                k.file_path
            FROM controlled_revisions r
            JOIN kb_documents k
              ON k.doc_id = r.kb_doc_id
            WHERE r.controlled_document_id = ?
            ORDER BY r.revision_no DESC, r.created_at_ms DESC
            """,
            (controlled_document_id,),
        ).fetchall()

    def _load_document(self, conn, *, controlled_document_id: str) -> ControlledDocument:
        row = conn.execute(
            """
            SELECT
                controlled_document_id,
                doc_code,
                title,
                document_type,
                product_name,
                registration_ref,
                target_kb_id,
                target_kb_name,
                current_revision_id,
                effective_revision_id,
                created_by,
                created_at_ms,
                updated_at_ms
            FROM controlled_documents
            WHERE controlled_document_id = ?
            """,
            (controlled_document_id,),
        ).fetchone()
        if row is None:
            raise DocumentControlError("controlled_document_not_found", status_code=404)
        revisions = [
            self._revision_from_joined_row(item)
            for item in self._get_revision_rows(conn, controlled_document_id=controlled_document_id)
        ]
        revisions_by_id = {item.controlled_revision_id: item for item in revisions}
        return self._document_from_row(
            row,
            current_revision=revisions_by_id.get(str(row["current_revision_id"])) if row["current_revision_id"] else None,
            effective_revision=revisions_by_id.get(str(row["effective_revision_id"])) if row["effective_revision_id"] else None,
            revisions=revisions,
        )

    def _load_revision(self, conn, *, controlled_revision_id: str) -> ControlledRevision:
        row = conn.execute(
            """
            SELECT
                r.controlled_revision_id,
                r.controlled_document_id,
                r.kb_doc_id,
                r.revision_no,
                r.status,
                r.change_summary,
                r.previous_revision_id,
                r.approved_by,
                r.approved_at_ms,
                r.effective_at_ms,
                r.obsolete_at_ms,
                r.created_by,
                r.created_at_ms,
                r.updated_at_ms,
                k.filename,
                k.file_size,
                k.mime_type,
                k.uploaded_by,
                k.uploaded_at_ms,
                k.reviewed_by,
                k.reviewed_at_ms,
                k.review_notes,
                k.ragflow_doc_id,
                k.kb_id,
                k.kb_dataset_id,
                k.kb_name,
                k.file_sha256,
                k.file_path
            FROM controlled_revisions r
            JOIN kb_documents k
              ON k.doc_id = r.kb_doc_id
            WHERE r.controlled_revision_id = ?
            """,
            (controlled_revision_id,),
        ).fetchone()
        if row is None:
            raise DocumentControlError("controlled_revision_not_found", status_code=404)
        return self._revision_from_joined_row(row)

    def list_documents(
        self,
        *,
        allowed_kb_refs: list[str] | None = None,
        doc_code: str | None = None,
        title: str | None = None,
        document_type: str | None = None,
        product_name: str | None = None,
        registration_ref: str | None = None,
        status: str | None = None,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ControlledDocument]:
        refs = [str(item).strip() for item in (allowed_kb_refs or []) if str(item).strip()]
        conn = self._connect()
        try:
            sql = """
                SELECT d.controlled_document_id
                FROM controlled_documents d
                LEFT JOIN controlled_revisions r
                  ON r.controlled_revision_id = d.current_revision_id
                WHERE 1 = 1
            """
            params: list[object] = []
            if refs:
                placeholders = ",".join("?" for _ in refs)
                sql += f" AND (d.target_kb_id IN ({placeholders}) OR d.target_kb_name IN ({placeholders}))"
                params.extend(refs)
                params.extend(refs)
            if doc_code:
                sql += " AND d.doc_code LIKE ?"
                params.append(f"%{str(doc_code).strip()}%")
            if title:
                sql += " AND d.title LIKE ?"
                params.append(f"%{str(title).strip()}%")
            if document_type:
                sql += " AND d.document_type = ?"
                params.append(str(document_type).strip())
            if product_name:
                sql += " AND IFNULL(d.product_name, '') LIKE ?"
                params.append(f"%{str(product_name).strip()}%")
            if registration_ref:
                sql += " AND IFNULL(d.registration_ref, '') LIKE ?"
                params.append(f"%{str(registration_ref).strip()}%")
            if status:
                sql += " AND IFNULL(r.status, '') = ?"
                params.append(str(status).strip())
            if query:
                sql += (
                    " AND (d.doc_code LIKE ? OR d.title LIKE ? OR IFNULL(d.product_name, '') LIKE ? "
                    "OR IFNULL(d.registration_ref, '') LIKE ?)"
                )
                pattern = f"%{str(query).strip()}%"
                params.extend([pattern, pattern, pattern, pattern])
            sql += " ORDER BY d.updated_at_ms DESC LIMIT ?"
            params.append(int(max(1, min(500, limit))))
            rows = conn.execute(sql, params).fetchall()
            return [self._load_document(conn, controlled_document_id=str(row["controlled_document_id"])) for row in rows]
        finally:
            conn.close()

    def get_document(self, *, controlled_document_id: str) -> ControlledDocument:
        conn = self._connect()
        try:
            return self._load_document(conn, controlled_document_id=controlled_document_id)
        finally:
            conn.close()

    def get_revision(self, *, controlled_revision_id: str) -> ControlledRevision:
        conn = self._connect()
        try:
            return self._load_revision(conn, controlled_revision_id=controlled_revision_id)
        finally:
            conn.close()

    def _insert_controlled_document(
        self,
        conn,
        *,
        controlled_document_id: str,
        doc_code: str,
        title: str,
        document_type: str,
        product_name: str | None,
        registration_ref: str | None,
        target_kb_id: str,
        target_kb_name: str | None,
        revision_id: str,
        created_by: str,
        now_ms: int,
    ) -> None:
        conn.execute(
            """
            INSERT INTO controlled_documents (
                controlled_document_id,
                doc_code,
                title,
                document_type,
                product_name,
                registration_ref,
                target_kb_id,
                target_kb_name,
                current_revision_id,
                effective_revision_id,
                created_by,
                created_at_ms,
                updated_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                controlled_document_id,
                doc_code,
                title,
                document_type,
                product_name,
                registration_ref,
                target_kb_id,
                target_kb_name,
                revision_id,
                None,
                created_by,
                now_ms,
                now_ms,
            ),
        )

    def _insert_controlled_revision(
        self,
        conn,
        *,
        revision_id: str,
        controlled_document_id: str,
        kb_doc_id: str,
        revision_no: int,
        change_summary: str | None,
        previous_revision_id: str | None,
        created_by: str,
        now_ms: int,
    ) -> None:
        conn.execute(
            """
            INSERT INTO controlled_revisions (
                controlled_revision_id,
                controlled_document_id,
                kb_doc_id,
                revision_no,
                status,
                change_summary,
                previous_revision_id,
                approved_by,
                approved_at_ms,
                effective_at_ms,
                obsolete_at_ms,
                created_by,
                created_at_ms,
                updated_at_ms
            ) VALUES (?, ?, ?, ?, 'draft', ?, ?, NULL, NULL, NULL, NULL, ?, ?, ?)
            """,
            (
                revision_id,
                controlled_document_id,
                kb_doc_id,
                revision_no,
                change_summary,
                previous_revision_id,
                created_by,
                now_ms,
                now_ms,
            ),
        )

    def _cleanup_failed_create(self, *, kb_doc_id: str | None, file_path: Path | None) -> None:
        if kb_doc_id:
            try:
                self._deps.kb_store.delete_document(kb_doc_id)
            except Exception:
                pass
        if file_path and file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass

    def create_document(
        self,
        *,
        doc_code: str,
        title: str,
        document_type: str,
        target_kb_id: str,
        created_by: str,
        upload_file,
        product_name: str | None = None,
        registration_ref: str | None = None,
        change_summary: str | None = None,
    ) -> ControlledDocument:
        clean_doc_code = self._require_text(doc_code, "doc_code_required")
        clean_title = self._require_text(title, "title_required")
        clean_type = self._require_text(document_type, "document_type_required")
        clean_target_kb = self._require_text(target_kb_id, "target_kb_id_required")
        clean_created_by = self._require_text(created_by, "created_by_required")
        controlled_document_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        now_ms = self._now_ms()
        file_path: Path | None = None
        kb_doc = None

        try:
            content = upload_file.file.read() if hasattr(upload_file, "file") else upload_file.read()
            filename = str(getattr(upload_file, "filename", "") or "").strip()
            display_name, file_path = self._staged_file_path(doc_code=clean_doc_code, revision_no=1, upload_filename=filename)
            self._write_upload(path=file_path, content=content)
            mime_type = self._detect_mime(display_name, getattr(upload_file, "content_type", None))
            kb_id, kb_dataset_id, kb_name = self._resolve_kb_info(clean_target_kb)
            kb_doc = self._create_kb_document(
                controlled_document_id=controlled_document_id,
                revision_no=1,
                file_path=file_path,
                filename=display_name,
                mime_type=mime_type,
                uploaded_by=clean_created_by,
                kb_id=kb_id,
                kb_dataset_id=kb_dataset_id,
                kb_name=kb_name,
                previous_doc_id=None,
                is_current=True,
            )

            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._insert_controlled_document(
                    conn,
                    controlled_document_id=controlled_document_id,
                    doc_code=clean_doc_code,
                    title=clean_title,
                    document_type=clean_type,
                    product_name=(str(product_name).strip() if product_name else None),
                    registration_ref=(str(registration_ref).strip() if registration_ref else None),
                    target_kb_id=kb_id,
                    target_kb_name=kb_name,
                    revision_id=revision_id,
                    created_by=clean_created_by,
                    now_ms=now_ms,
                )
                self._insert_controlled_revision(
                    conn,
                    revision_id=revision_id,
                    controlled_document_id=controlled_document_id,
                    kb_doc_id=kb_doc.doc_id,
                    revision_no=1,
                    change_summary=(str(change_summary).strip() if change_summary else None),
                    previous_revision_id=None,
                    created_by=clean_created_by,
                    now_ms=now_ms,
                )
                conn.commit()
            finally:
                conn.close()
            return self.get_document(controlled_document_id=controlled_document_id)
        except sqlite3.IntegrityError as exc:
            self._cleanup_failed_create(kb_doc_id=(kb_doc.doc_id if kb_doc else None), file_path=file_path)
            raise self._map_integrity_error(exc) from exc
        except Exception:
            self._cleanup_failed_create(kb_doc_id=(kb_doc.doc_id if kb_doc else None), file_path=file_path)
            raise

    def create_revision(
        self,
        *,
        controlled_document_id: str,
        created_by: str,
        upload_file,
        change_summary: str | None = None,
    ) -> ControlledDocument:
        clean_document_id = self._require_text(controlled_document_id, "controlled_document_id_required")
        clean_created_by = self._require_text(created_by, "created_by_required")

        conn = self._connect()
        try:
            document = self._load_document(conn, controlled_document_id=clean_document_id)
            current_revision = document.current_revision
            if current_revision is not None and current_revision.status != "effective":
                raise DocumentControlError("current_revision_not_stable")
            next_revision_no = 1
            if document.revisions:
                next_revision_no = max(item.revision_no for item in document.revisions) + 1
            previous_revision_id = current_revision.controlled_revision_id if current_revision is not None else None
            previous_doc_id = current_revision.kb_doc_id if current_revision is not None else None
        finally:
            conn.close()

        revision_id = str(uuid.uuid4())
        now_ms = self._now_ms()
        file_path: Path | None = None
        kb_doc = None
        try:
            content = upload_file.file.read() if hasattr(upload_file, "file") else upload_file.read()
            filename = str(getattr(upload_file, "filename", "") or "").strip()
            display_name, file_path = self._staged_file_path(
                doc_code=document.doc_code,
                revision_no=next_revision_no,
                upload_filename=filename,
            )
            self._write_upload(path=file_path, content=content)
            mime_type = self._detect_mime(display_name, getattr(upload_file, "content_type", None))
            kb_id, kb_dataset_id, kb_name = self._resolve_kb_info(document.target_kb_id or (document.target_kb_name or ""))
            kb_doc = self._create_kb_document(
                controlled_document_id=clean_document_id,
                revision_no=next_revision_no,
                file_path=file_path,
                filename=display_name,
                mime_type=mime_type,
                uploaded_by=clean_created_by,
                kb_id=kb_id,
                kb_dataset_id=kb_dataset_id,
                kb_name=kb_name,
                previous_doc_id=previous_doc_id,
                is_current=False,
            )

            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._insert_controlled_revision(
                    conn,
                    revision_id=revision_id,
                    controlled_document_id=clean_document_id,
                    kb_doc_id=kb_doc.doc_id,
                    revision_no=next_revision_no,
                    change_summary=(str(change_summary).strip() if change_summary else None),
                    previous_revision_id=previous_revision_id,
                    created_by=clean_created_by,
                    now_ms=now_ms,
                )
                conn.execute(
                    """
                    UPDATE controlled_documents
                    SET current_revision_id = ?, updated_at_ms = ?
                    WHERE controlled_document_id = ?
                    """,
                    (revision_id, now_ms, clean_document_id),
                )
                conn.commit()
            finally:
                conn.close()
            return self.get_document(controlled_document_id=clean_document_id)
        except sqlite3.IntegrityError as exc:
            self._cleanup_failed_create(kb_doc_id=(kb_doc.doc_id if kb_doc else None), file_path=file_path)
            raise self._map_integrity_error(exc) from exc
        except Exception:
            self._cleanup_failed_create(kb_doc_id=(kb_doc.doc_id if kb_doc else None), file_path=file_path)
            raise

    def _emit_lifecycle_audit(
        self,
        *,
        ctx,
        revision: ControlledRevision,
        event_type: str,
        before: dict[str, object],
        after: dict[str, object],
        note: str | None,
    ) -> None:
        manager = getattr(self._deps, "audit_log_manager", None)
        if manager is not None:
            manager.safe_log_ctx_event(
                ctx=ctx,
                action="document_control_transition",
                source="document_control",
                resource_type="controlled_revision",
                resource_id=revision.controlled_revision_id,
                event_type=event_type,
                before=before,
                after=after,
                reason=note,
                doc_id=revision.kb_doc_id,
                filename=revision.filename,
                kb_id=(revision.kb_name or revision.kb_id),
                kb_dataset_id=revision.kb_dataset_id,
                kb_name=(revision.kb_name or revision.kb_id),
                meta={"controlled_document_id": revision.controlled_document_id, "revision_no": revision.revision_no},
            )
            return

        store = getattr(self._deps, "audit_log_store", None)
        if store is None:
            return
        store.log_event(
            action="document_control_transition",
            actor=ctx.payload.sub,
            source="document_control",
            resource_type="controlled_revision",
            resource_id=revision.controlled_revision_id,
            event_type=event_type,
            before=before,
            after=after,
            reason=note,
            doc_id=revision.kb_doc_id,
            filename=revision.filename,
            kb_id=(revision.kb_name or revision.kb_id),
            kb_dataset_id=revision.kb_dataset_id,
            kb_name=(revision.kb_name or revision.kb_id),
            meta={"controlled_document_id": revision.controlled_document_id, "revision_no": revision.revision_no},
            **actor_fields_from_ctx(self._deps, ctx),
        )

    def _transition_simple(self, *, conn, revision: ControlledRevision, target_status: str, actor_user_id: str, note: str | None) -> None:
        now_ms = self._now_ms()
        approved_by = revision.approved_by
        approved_at_ms = revision.approved_at_ms
        if target_status == "approved":
            approved_by = actor_user_id
            approved_at_ms = now_ms

        conn.execute(
            """
            UPDATE controlled_revisions
            SET status = ?,
                approved_by = ?,
                approved_at_ms = ?,
                updated_at_ms = ?
            WHERE controlled_revision_id = ?
            """,
            (
                target_status,
                approved_by,
                approved_at_ms,
                now_ms,
                revision.controlled_revision_id,
            ),
        )
        conn.execute(
            """
            UPDATE controlled_documents
            SET updated_at_ms = ?
            WHERE controlled_document_id = ?
            """,
            (now_ms, revision.controlled_document_id),
        )
        conn.execute(
            """
            UPDATE kb_documents
            SET status = ?,
                reviewed_by = ?,
                reviewed_at_ms = ?,
                review_notes = ?,
                effective_status = ?
            WHERE doc_id = ?
            """,
            (
                target_status,
                actor_user_id,
                now_ms,
                note,
                target_status,
                revision.kb_doc_id,
            ),
        )

    def _delete_ragflow_document(self, *, revision: ControlledRevision) -> None:
        ragflow_doc_id = str(revision.ragflow_doc_id or "").strip()
        if not ragflow_doc_id:
            return
        dataset_ref = revision.kb_dataset_id or revision.kb_id or (revision.kb_name or "")
        try:
            success = bool(self._deps.ragflow_service.delete_document(ragflow_doc_id, dataset_name=dataset_ref))
        except Exception as exc:
            raise DocumentControlError(f"ragflow_delete_failed:{exc}", status_code=500) from exc
        if not success:
            raise DocumentControlError("ragflow_delete_failed", status_code=500)

    def _finalize_kb_doc_for_effective(self, *, kb_doc) -> str | None:
        file_path = Path(str(getattr(kb_doc, "file_path", "") or ""))
        if not file_path.exists():
            raise DocumentControlError("local_file_missing", status_code=409)

        try:
            file_content = file_path.read_bytes()
        except Exception as exc:
            raise DocumentControlError(f"read_file_failed:{exc}", status_code=500) from exc

        try:
            ragflow_doc_id = self._deps.ragflow_service.upload_document_blob(
                file_filename=str(getattr(kb_doc, "filename", "") or file_path.name),
                file_content=file_content,
                kb_id=str(getattr(kb_doc, "kb_id", "") or ""),
            )
        except Exception as exc:
            raise DocumentControlError(f"ragflow_upload_failed:{exc}", status_code=500) from exc

        if not ragflow_doc_id:
            raise DocumentControlError("ragflow_upload_failed", status_code=500)

        dataset_ref = (
            str(getattr(kb_doc, "kb_dataset_id", "") or "").strip()
            or str(getattr(kb_doc, "kb_id", "") or "").strip()
            or str(getattr(kb_doc, "kb_name", "") or "").strip()
        )
        if ragflow_doc_id == "uploaded":
            return str(ragflow_doc_id)

        try:
            parsed = self._deps.ragflow_service.parse_document(
                dataset_ref=dataset_ref,
                document_id=str(ragflow_doc_id),
            )
        except Exception as exc:
            raise DocumentControlError(f"ragflow_parse_failed:{exc}", status_code=500) from exc
        if not parsed:
            raise DocumentControlError("ragflow_parse_failed", status_code=500)
        return str(ragflow_doc_id)

    def _make_revision_effective(
        self,
        *,
        conn,
        ctx,
        revision: ControlledRevision,
        note: str | None,
        pending_audits: list[dict[str, object]],
    ) -> None:
        now_ms = self._now_ms()
        document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
        previous_effective = document.effective_revision
        kb_doc = self._deps.kb_store.get_document(revision.kb_doc_id)
        if kb_doc is None:
            raise DocumentControlError("kb_document_not_found", status_code=409)

        if not getattr(kb_doc, "ragflow_doc_id", None):
            try:
                ragflow_doc_id = self._finalize_kb_doc_for_effective(kb_doc=kb_doc)
            except Exception as exc:
                raise DocumentControlError(f"document_finalize_failed:{exc}", status_code=500) from exc
        else:
            ragflow_doc_id = getattr(kb_doc, "ragflow_doc_id", None)

        if previous_effective is not None and previous_effective.controlled_revision_id != revision.controlled_revision_id:
            before_obsolete = previous_effective.as_dict()
            self._delete_ragflow_document(revision=previous_effective)
            conn.execute(
                """
                UPDATE controlled_revisions
                SET status = 'obsolete',
                    obsolete_at_ms = ?,
                    updated_at_ms = ?
                WHERE controlled_revision_id = ?
                """,
                (now_ms, now_ms, previous_effective.controlled_revision_id),
            )
            conn.execute(
                """
                UPDATE kb_documents
                SET status = 'obsolete',
                    reviewed_by = ?,
                    reviewed_at_ms = ?,
                    review_notes = ?,
                    ragflow_doc_id = NULL,
                    is_current = 0,
                    effective_status = 'obsolete'
                WHERE doc_id = ?
                """,
                (
                    ctx.payload.sub,
                    now_ms,
                    note,
                    previous_effective.kb_doc_id,
                ),
            )
            obsolete_after = self._load_revision(conn, controlled_revision_id=previous_effective.controlled_revision_id)
            pending_audits.append(
                {
                    "ctx": ctx,
                    "revision": obsolete_after,
                    "event_type": "controlled_revision_obsolete",
                    "before": before_obsolete,
                    "after": obsolete_after.as_dict(),
                    "note": note,
                }
            )

        conn.execute(
            """
            UPDATE controlled_revisions
            SET status = 'effective',
                approved_by = COALESCE(approved_by, ?),
                approved_at_ms = COALESCE(approved_at_ms, ?),
                effective_at_ms = ?,
                updated_at_ms = ?
            WHERE controlled_revision_id = ?
            """,
            (
                ctx.payload.sub,
                now_ms,
                now_ms,
                now_ms,
                revision.controlled_revision_id,
            ),
        )
        conn.execute(
            """
            UPDATE controlled_documents
            SET current_revision_id = ?,
                effective_revision_id = ?,
                updated_at_ms = ?
            WHERE controlled_document_id = ?
            """,
            (
                revision.controlled_revision_id,
                revision.controlled_revision_id,
                now_ms,
                revision.controlled_document_id,
            ),
        )
        conn.execute(
            """
            UPDATE kb_documents
            SET status = 'effective',
                reviewed_by = ?,
                reviewed_at_ms = ?,
                review_notes = ?,
                ragflow_doc_id = ?,
                is_current = 1,
                effective_status = 'effective'
            WHERE doc_id = ?
            """,
            (
                ctx.payload.sub,
                now_ms,
                note or f"controlled_revision_effective:{revision.controlled_revision_id}",
                ragflow_doc_id,
                revision.kb_doc_id,
            ),
        )
        effective_after = self._load_revision(conn, controlled_revision_id=revision.controlled_revision_id)
        pending_audits.append(
            {
                "ctx": ctx,
                "revision": effective_after,
                "event_type": "controlled_revision_effective",
                "before": revision.as_dict(),
                "after": effective_after.as_dict(),
                "note": note,
            }
        )

    def _mark_revision_obsolete(
        self,
        *,
        conn,
        ctx,
        revision: ControlledRevision,
        note: str | None,
        pending_audits: list[dict[str, object]],
    ) -> None:
        now_ms = self._now_ms()
        before = revision.as_dict()
        self._delete_ragflow_document(revision=revision)
        conn.execute(
            """
            UPDATE controlled_revisions
            SET status = 'obsolete',
                obsolete_at_ms = ?,
                updated_at_ms = ?
            WHERE controlled_revision_id = ?
            """,
            (now_ms, now_ms, revision.controlled_revision_id),
        )
        conn.execute(
            """
            UPDATE controlled_documents
            SET effective_revision_id = NULL,
                updated_at_ms = ?
            WHERE controlled_document_id = ?
            """,
            (now_ms, revision.controlled_document_id),
        )
        conn.execute(
            """
            UPDATE kb_documents
            SET status = 'obsolete',
                reviewed_by = ?,
                reviewed_at_ms = ?,
                review_notes = ?,
                ragflow_doc_id = NULL,
                is_current = 0,
                effective_status = 'obsolete'
            WHERE doc_id = ?
            """,
            (
                ctx.payload.sub,
                now_ms,
                note,
                revision.kb_doc_id,
            ),
        )
        obsolete_after = self._load_revision(conn, controlled_revision_id=revision.controlled_revision_id)
        pending_audits.append(
            {
                "ctx": ctx,
                "revision": obsolete_after,
                "event_type": "controlled_revision_obsolete",
                "before": before,
                "after": obsolete_after.as_dict(),
                "note": note,
            }
        )

    def transition_revision(self, *, controlled_revision_id: str, target_status: str, ctx, note: str | None = None) -> ControlledDocument:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        clean_target_status = self._require_text(target_status, "target_status_required")
        if clean_target_status not in ALLOWED_STATUSES:
            raise DocumentControlError("invalid_target_status")

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            if revision.status == clean_target_status:
                raise DocumentControlError("revision_status_unchanged")
            if clean_target_status not in ALLOWED_TRANSITIONS.get(revision.status, set()):
                raise DocumentControlError("invalid_revision_transition")

            pending_audits: list[dict[str, object]] = []
            if clean_target_status == "effective":
                self._make_revision_effective(
                    conn=conn,
                    ctx=ctx,
                    revision=revision,
                    note=note,
                    pending_audits=pending_audits,
                )
            elif clean_target_status == "obsolete":
                self._mark_revision_obsolete(
                    conn=conn,
                    ctx=ctx,
                    revision=revision,
                    note=note,
                    pending_audits=pending_audits,
                )
            else:
                self._transition_simple(
                    conn=conn,
                    revision=revision,
                    target_status=clean_target_status,
                    actor_user_id=str(ctx.payload.sub),
                    note=note,
                )

            conn.commit()
            document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
        finally:
            conn.close()
        for event in pending_audits:
            self._emit_lifecycle_audit(**event)
        return document

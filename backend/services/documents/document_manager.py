from __future__ import annotations

import os
import urllib.parse
import logging
import time
from dataclasses import dataclass

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response

from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import (
    assert_can_delete,
    assert_can_download,
    assert_can_review,
    assert_kb_allowed,
)
from backend.services.documents.errors import DocumentNotFound, DocumentSourceError
from backend.services.documents.models import DeleteResult, DocumentRef
from backend.services.documents.sources.knowledge_source import KnowledgeDocumentSource
from backend.services.documents.sources.ragflow_source import RagflowDocumentSource
from backend.services.audit_helpers import actor_fields_from_ctx
from backend.app.core.request_id import get_request_id

logger = logging.getLogger(__name__)


@dataclass
class DocumentManager:
    deps: object

    def __post_init__(self) -> None:
        self._ragflow = RagflowDocumentSource(self.deps)
        self._knowledge = KnowledgeDocumentSource(self.deps)

    def _content_disposition(self, filename: str) -> str:
        try:
            filename.encode("ascii")
            return f'attachment; filename="{filename}"'
        except UnicodeEncodeError:
            ascii_filename = filename.encode("ascii", "replace").decode("ascii")
            encoded_filename = urllib.parse.quote(filename)
            return f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"

    # -------------------- Preview (JSON contract) --------------------

    def preview_payload(self, ref: DocumentRef, *, preview_filename: str | None = None, render: str = "default"):
        """
        Return a unified preview JSON payload.
        This is used by the unified preview gateway and can be reused by other modules.
        """
        t0 = time.perf_counter()
        request_id = get_request_id() or "-"
        fetch_t0 = time.perf_counter()
        if ref.source == "ragflow":
            doc_bytes = self._ragflow.get_bytes(ref)
        else:
            doc_bytes = self._knowledge.get_bytes(ref)
        source_fetch_ms = (time.perf_counter() - fetch_t0) * 1000

        from backend.services.unified_preview import build_preview_payload

        transform_t0 = time.perf_counter()
        payload = build_preview_payload(
            doc_bytes.content,
            preview_filename or doc_bytes.filename,
            doc_id=ref.doc_id,
            render=render,
        )
        transform_ms = (time.perf_counter() - transform_t0) * 1000
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "preview_payload_done request_id=%s source=%s doc_id=%s dataset=%s filename=%s size_bytes=%s render=%s type=%s source_fetch_ms=%.2f transform_ms=%.2f elapsed_ms=%.2f",
            request_id,
            ref.source,
            ref.doc_id,
            getattr(ref, "dataset_name", None),
            preview_filename or doc_bytes.filename,
            len(doc_bytes.content or b""),
            render,
            payload.get("type"),
            source_fetch_ms,
            transform_ms,
            elapsed_ms,
        )
        return payload

    # -------------------- Download --------------------

    def download_ragflow_response(self, *, doc_id: str, dataset: str, filename: str | None, ctx):
        snapshot = ctx.snapshot
        assert_can_download(snapshot)
        assert_kb_allowed(snapshot, resolve_kb_ref(self.deps, dataset).variants)

        try:
            doc_bytes = self._ragflow.get_bytes(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset))
        except DocumentNotFound as e:
            raise HTTPException(status_code=404, detail=str(e))
        except DocumentSourceError as e:
            raise HTTPException(status_code=500, detail=f"濞戞挸顑堝ù鍥ㄥ緞鏉堫偉袝: {str(e)}")

        final_filename = filename or doc_bytes.filename or f"document_{doc_id}"

        kb_id = dataset
        self.deps.download_log_store.log_download(
            doc_id=doc_id,
            filename=final_filename,
            kb_id=kb_id,
            downloaded_by=ctx.payload.sub,
            ragflow_doc_id=doc_id,
            is_batch=False,
            kb_dataset_id=None,
            kb_name=kb_id,
        )
        audit = getattr(self.deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_download",
                    actor=ctx.payload.sub,
                    source="ragflow",
                    doc_id=doc_id,
                    filename=final_filename,
                    kb_id=kb_id,
                    kb_name=kb_id,
                    meta={"is_batch": False},
                    **actor_fields_from_ctx(self.deps, ctx),
                )
            except Exception:
                pass

        return Response(
            content=doc_bytes.content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": self._content_disposition(final_filename)},
        )

    def download_knowledge_response(self, *, doc_id: str, ctx):
        deps = self.deps
        snapshot = ctx.snapshot
        assert_can_download(snapshot)

        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="document_not_found")

        assert_kb_allowed(snapshot, doc.kb_id)
        if not os.path.exists(doc.file_path):
            raise HTTPException(status_code=404, detail="file_not_found")

        deps.download_log_store.log_download(
            doc_id=doc.doc_id,
            filename=doc.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            downloaded_by=ctx.payload.sub,
            kb_dataset_id=doc.kb_dataset_id,
            kb_name=doc.kb_name,
        )
        audit = getattr(deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_download",
                    actor=ctx.payload.sub,
                    source="knowledge",
                    doc_id=doc.doc_id,
                    filename=doc.filename,
                    kb_id=(doc.kb_name or doc.kb_id),
                    kb_dataset_id=getattr(doc, "kb_dataset_id", None),
                    kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
                    meta={"is_batch": False},
                    **actor_fields_from_ctx(deps, ctx),
                )
            except Exception:
                pass
        return FileResponse(path=doc.file_path, filename=doc.filename, media_type=doc.mime_type)

    # -------------------- Upload (knowledge local staging) --------------------

    async def stage_upload_knowledge(self, *, kb_ref: str, upload_file, ctx):
        from backend.services.knowledge_ingestion import KnowledgeIngestionError, KnowledgeIngestionManager

        ingestion_manager = getattr(self.deps, "knowledge_ingestion_manager", None)
        if ingestion_manager is None:
            ingestion_manager = KnowledgeIngestionManager(deps=self.deps)
        try:
            return await ingestion_manager.stage_upload_knowledge(kb_ref=kb_ref, upload_file=upload_file, ctx=ctx)
        except KnowledgeIngestionError as e:
            raise HTTPException(status_code=e.status_code, detail=e.code) from e
    # -------------------- Delete --------------------

    def delete_knowledge_document(self, *, doc_id: str, ctx) -> DeleteResult:
        deps = self.deps
        snapshot = ctx.snapshot
        assert_can_delete(snapshot)

        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="document_not_found")
        assert_kb_allowed(snapshot, doc.kb_id)

        ragflow_ok = None
        ragflow_err = None
        if doc.ragflow_doc_id:
            dataset_ref = doc.kb_dataset_id or doc.kb_id or (doc.kb_name or "")
            try:
                ragflow_ok = 1 if deps.ragflow_service.delete_document(doc.ragflow_doc_id, dataset_name=dataset_ref) else 0
            except Exception as e:
                ragflow_ok = 0
                ragflow_err = str(e)
            if ragflow_ok == 0 and not ragflow_err:
                ragflow_err = "ragflow_delete_failed"

        deps.deletion_log_store.log_deletion(
            doc_id=doc.doc_id,
            filename=doc.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            deleted_by=ctx.payload.sub,
            kb_dataset_id=doc.kb_dataset_id,
            kb_name=doc.kb_name,
            original_uploader=doc.uploaded_by,
            original_reviewer=doc.reviewed_by,
            ragflow_doc_id=doc.ragflow_doc_id,
            action="delete",
            ragflow_deleted=ragflow_ok,
            ragflow_delete_error=ragflow_err,
        )
        audit = getattr(deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_delete",
                    actor=ctx.payload.sub,
                    source="knowledge",
                    doc_id=doc.doc_id,
                    filename=doc.filename,
                    kb_id=(doc.kb_name or doc.kb_id),
                    kb_dataset_id=getattr(doc, "kb_dataset_id", None),
                    kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
                    meta={"ragflow_deleted": bool(ragflow_ok == 1) if ragflow_ok is not None else None},
                    **actor_fields_from_ctx(deps, ctx),
                )
            except Exception:
                pass

        if ragflow_ok == 0:
            raise HTTPException(status_code=500, detail=f"ragflow_delete_failed:{ragflow_err}")

        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        deps.kb_store.delete_document(doc_id)

        return DeleteResult(ok=True, message="document_deleted", ragflow_deleted=(ragflow_ok == 1 if ragflow_ok is not None else None))

    def delete_ragflow_document(self, *, doc_id: str, dataset_name: str, ctx) -> DeleteResult:
        snapshot = ctx.snapshot
        assert_can_delete(snapshot)
        assert_kb_allowed(snapshot, resolve_kb_ref(self.deps, dataset_name).variants)

        kb_info = None
        local_doc = None
        try:
            kb_info = resolve_kb_ref(self.deps, dataset_name)
            local_doc = self.deps.kb_store.get_document_by_ragflow_id(doc_id, dataset_name, kb_refs=list(kb_info.variants))
        except Exception:
            kb_info = None
            local_doc = None

        success = self._ragflow.delete(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset_name))
        if not success:
            raise HTTPException(status_code=404, detail="document_not_found_or_delete_failed")

        audit = getattr(self.deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_delete",
                    actor=ctx.payload.sub,
                    source="ragflow",
                    doc_id=doc_id,
                    filename=(local_doc.filename if local_doc else None),
                    kb_id=(getattr(local_doc, "kb_name", None) or getattr(local_doc, "kb_id", None) or dataset_name),
                    kb_dataset_id=getattr(local_doc, "kb_dataset_id", None) if local_doc else None,
                    kb_name=getattr(local_doc, "kb_name", None) if local_doc else dataset_name,
                    meta={"ragflow_deleted": True},
                    **actor_fields_from_ctx(self.deps, ctx),
                )
            except Exception:
                pass

        if local_doc:
            self.deps.deletion_log_store.log_deletion(
                doc_id=local_doc.doc_id,
                filename=local_doc.filename,
                kb_id=local_doc.kb_id,
                deleted_by=ctx.payload.sub,
                kb_dataset_id=getattr(local_doc, "kb_dataset_id", None),
                kb_name=getattr(local_doc, "kb_name", None),
                original_uploader=local_doc.uploaded_by,
                original_reviewer=local_doc.reviewed_by,
                ragflow_doc_id=doc_id,
            )
            if os.path.exists(local_doc.file_path):
                os.remove(local_doc.file_path)
            self.deps.kb_store.delete_document(local_doc.doc_id)

        return DeleteResult(ok=True, message="document_deleted", ragflow_deleted=True)

    # -------------------- Review preview policy --------------------

    def assert_can_preview_knowledge(self, snapshot):
        try:
            assert_can_download(snapshot)
        except Exception:
            assert_can_review(snapshot)

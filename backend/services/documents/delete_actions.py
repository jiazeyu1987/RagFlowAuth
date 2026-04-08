from __future__ import annotations

import os

from fastapi import HTTPException

from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import assert_can_delete, assert_kb_allowed
from backend.services.audit_helpers import actor_fields_from_ctx, actor_fields_from_user
from backend.services.documents.models import DeleteResult, DocumentRef


class DocumentDeleteActions:
    def __init__(
        self,
        *,
        deps,
        ragflow_source,
    ):
        self._deps = deps
        self._ragflow = ragflow_source

    def _delete_ragflow_copy(self, doc) -> tuple[int | None, str | None]:
        if not getattr(doc, "ragflow_doc_id", None):
            return None, None

        dataset_ref = doc.kb_dataset_id or doc.kb_id or (doc.kb_name or "")
        ragflow_ok = None
        ragflow_err = None
        try:
            ragflow_ok = 1 if self._deps.ragflow_service.delete_document(doc.ragflow_doc_id, dataset_name=dataset_ref) else 0
        except Exception as exc:
            ragflow_ok = 0
            ragflow_err = str(exc)
        if ragflow_ok == 0 and not ragflow_err:
            ragflow_err = "ragflow_delete_failed"
        return ragflow_ok, ragflow_err

    def _remove_local_document(self, doc) -> None:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        self._deps.kb_store.delete_document(doc.doc_id)

    def _log_knowledge_deletion(
        self,
        *,
        doc,
        deleted_by: str,
        ragflow_ok: int | None,
        ragflow_err: str | None,
    ) -> None:
        self._deps.deletion_log_store.log_deletion(
            doc_id=doc.doc_id,
            filename=doc.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            deleted_by=deleted_by,
            kb_dataset_id=doc.kb_dataset_id,
            kb_name=doc.kb_name,
            original_uploader=doc.uploaded_by,
            original_reviewer=doc.reviewed_by,
            ragflow_doc_id=doc.ragflow_doc_id,
            action="delete",
            ragflow_deleted=ragflow_ok,
            ragflow_delete_error=ragflow_err,
        )

    def _log_knowledge_delete_audit(
        self,
        *,
        doc,
        actor_user_id: str,
        ragflow_ok: int | None,
        approval_request_id: str | None = None,
        ctx=None,
        actor_user=None,
    ) -> None:
        audit = getattr(self._deps, "audit_log_store", None)
        if audit:
            try:
                meta = {"ragflow_deleted": bool(ragflow_ok == 1) if ragflow_ok is not None else None}
                if approval_request_id:
                    meta["approval_request_id"] = approval_request_id
                audit_kwargs = {}
                if ctx is not None:
                    audit_kwargs = actor_fields_from_ctx(self._deps, ctx)
                elif actor_user is not None:
                    audit_kwargs = actor_fields_from_user(self._deps, actor_user)
                audit.log_event(
                    action="document_delete",
                    actor=actor_user_id,
                    source="knowledge",
                    doc_id=doc.doc_id,
                    filename=doc.filename,
                    kb_id=(doc.kb_name or doc.kb_id),
                    kb_dataset_id=getattr(doc, "kb_dataset_id", None),
                    kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
                    meta=meta,
                    **audit_kwargs,
                )
            except Exception:
                pass

    def _delete_knowledge_document(
        self,
        *,
        doc_id: str,
        actor_user_id: str,
        actor_user=None,
        approval_request_id: str | None = None,
        snapshot=None,
        ctx=None,
    ) -> DeleteResult:
        doc = self._deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="document_not_found")
        if snapshot is not None:
            assert_kb_allowed(snapshot, doc.kb_id)

        ragflow_ok, ragflow_err = self._delete_ragflow_copy(doc)
        self._log_knowledge_deletion(
            doc=doc,
            deleted_by=actor_user_id,
            ragflow_ok=ragflow_ok,
            ragflow_err=ragflow_err,
        )
        self._log_knowledge_delete_audit(
            doc=doc,
            actor_user_id=actor_user_id,
            ragflow_ok=ragflow_ok,
            approval_request_id=approval_request_id,
            ctx=ctx,
            actor_user=actor_user,
        )

        if ragflow_ok == 0:
            raise HTTPException(status_code=500, detail=f"ragflow_delete_failed:{ragflow_err}")

        self._remove_local_document(doc)
        return DeleteResult(
            ok=True,
            message="document_deleted",
            ragflow_deleted=(ragflow_ok == 1 if ragflow_ok is not None else None),
        )

    def delete_knowledge_document(self, *, doc_id: str, ctx) -> DeleteResult:
        snapshot = ctx.snapshot
        assert_can_delete(snapshot)
        return self._delete_knowledge_document(
            doc_id=doc_id,
            actor_user_id=ctx.payload.sub,
            snapshot=snapshot,
            ctx=ctx,
        )

    def delete_knowledge_document_trusted(
        self,
        *,
        doc_id: str,
        actor_user_id: str,
        actor_user=None,
        approval_request_id: str | None = None,
    ) -> DeleteResult:
        return self._delete_knowledge_document(
            doc_id=doc_id,
            actor_user_id=actor_user_id,
            actor_user=actor_user,
            approval_request_id=approval_request_id,
        )

    def delete_ragflow_document(self, *, doc_id: str, dataset_name: str, ctx) -> DeleteResult:
        snapshot = ctx.snapshot
        assert_can_delete(snapshot)

        kb_info = resolve_kb_ref(self._deps, dataset_name)
        assert_kb_allowed(snapshot, kb_info.variants)

        local_doc = None
        try:
            local_doc = self._deps.kb_store.get_document_by_ragflow_id(doc_id, dataset_name, kb_refs=list(kb_info.variants))
        except Exception:
            local_doc = None

        success = self._ragflow.delete(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset_name))
        if not success:
            raise HTTPException(status_code=404, detail="document_not_found_or_delete_failed")

        audit = getattr(self._deps, "audit_log_store", None)
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
                    **actor_fields_from_ctx(self._deps, ctx),
                )
            except Exception:
                pass

        if local_doc:
            self._deps.deletion_log_store.log_deletion(
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
            self._remove_local_document(local_doc)

        return DeleteResult(ok=True, message="document_deleted", ragflow_deleted=True)

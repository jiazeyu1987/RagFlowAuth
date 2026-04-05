from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.paths import resolve_repo_path
from backend.app.core.permission_resolver import assert_can_delete, assert_can_upload, assert_kb_allowed
from backend.services.audit_helpers import actor_fields_from_user
from backend.services.documents.document_manager import DocumentManager
from backend.services.knowledge_ingestion import KnowledgeIngestionManager

from .types import (
    INTERNAL_OPERATION_TYPE_LEGACY_DOCUMENT_REVIEW,
    OperationApprovalArtifact,
    OperationExecutionError,
    PreparedOperationRequest,
)


def _sha256_for_file(file_path: str) -> str:
    digest = hashlib.sha256()
    with Path(file_path).open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _staging_root() -> Path:
    root = resolve_repo_path(settings.UPLOAD_DIR) / "operation_approval_staging"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _dataset_local_document_count(
    deps: Any,
    *,
    dataset_ref: str | None = None,
    dataset_id: str | None = None,
    dataset_name: str | None = None,
) -> int:
    kb_store = getattr(deps, "kb_store", None)
    if kb_store is None:
        return 0

    refs: list[str] = []
    for candidate in (dataset_ref, dataset_id, dataset_name):
        clean = str(candidate or "").strip()
        if clean and clean not in refs:
            refs.append(clean)

    base_ref = next(
        (
            str(candidate).strip()
            for candidate in (dataset_id, dataset_ref, dataset_name)
            if str(candidate or "").strip()
        ),
        "",
    )
    if base_ref:
        kb_info = resolve_kb_ref(deps, base_ref)
        for candidate in kb_info.variants:
            clean = str(candidate or "").strip()
            if clean and clean not in refs:
                refs.append(clean)

    if not refs:
        return 0
    return int(kb_store.count_documents(kb_refs=refs))


class BaseOperationApprovalHandler:
    operation_type: str

    async def prepare_request(self, *, request_id: str, ctx: Any, **kwargs) -> PreparedOperationRequest:
        raise NotImplementedError

    def execute_request(self, *, request_data: dict, deps: Any, applicant_user: Any) -> dict:
        raise NotImplementedError

    def reject_request(
        self,
        *,
        request_data: dict,
        deps: Any,
        actor_user: Any,
        notes: str | None,
        signature_id: str,
    ) -> None:
        return None


class KnowledgeFileUploadApprovalHandler(BaseOperationApprovalHandler):
    operation_type = "knowledge_file_upload"

    async def prepare_request(self, *, request_id: str, ctx: Any, upload_file, kb_ref: str) -> PreparedOperationRequest:
        deps = ctx.deps
        snapshot = ctx.snapshot
        kb_info = resolve_kb_ref(deps, kb_ref)
        assert_can_upload(snapshot)
        assert_kb_allowed(snapshot, kb_info.variants)
        content = await upload_file.read()
        display_name, relative_path = KnowledgeIngestionManager._normalize_relative_upload_path(upload_file.filename)
        file_ext = Path(display_name).suffix.lower()
        allowed_extensions = set(settings.ALLOWED_EXTENSIONS)
        if getattr(deps, "upload_settings_store", None) is not None:
            allowed_extensions = set(deps.upload_settings_store.get().allowed_extensions)
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="unsupported_file_type")

        staging_path = _staging_root() / request_id / relative_path
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        staging_path.write_bytes(content)
        mime_type = KnowledgeIngestionManager._detect_mime(display_name, getattr(upload_file, "content_type", None))
        artifact = OperationApprovalArtifact(
            artifact_type="knowledge_file_upload",
            file_path=str(staging_path),
            file_name=display_name,
            mime_type=mime_type,
            size_bytes=len(content),
            sha256=_sha256_for_file(str(staging_path)),
            meta={"kb_ref": kb_ref},
        )
        target_ref = kb_info.dataset_id or kb_ref
        target_label = kb_info.name or kb_ref
        return PreparedOperationRequest(
            operation_type=self.operation_type,
            target_ref=target_ref,
            target_label=target_label,
            summary={
                "filename": display_name,
                "kb_ref": kb_ref,
                "kb_id": target_ref,
                "kb_name": target_label,
                "file_size": len(content),
                "mime_type": mime_type,
            },
            payload={
                "filename": display_name,
                "relative_path": str(relative_path).replace("\\", "/"),
                "staged_path": str(staging_path),
                "mime_type": mime_type,
                "file_size": len(content),
                "kb_ref": kb_ref,
                "kb_id": (kb_info.dataset_id or kb_ref),
                "kb_dataset_id": kb_info.dataset_id,
                "kb_name": (kb_info.name or kb_ref),
            },
            artifacts=[artifact],
        )

    def execute_request(self, *, request_data: dict, deps: Any, applicant_user: Any) -> dict:
        payload = request_data.get("payload") or {}
        staged_path = Path(str(payload.get("staged_path") or ""))
        if not staged_path.exists():
            raise OperationExecutionError("upload_staged_file_missing", status_code=409)
        final_root = resolve_repo_path(settings.UPLOAD_DIR) / str(request_data["request_id"])
        final_path = final_root / str(payload.get("relative_path") or staged_path.name)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged_path, final_path)

        doc = deps.kb_store.create_document(
            filename=str(payload.get("filename") or staged_path.name),
            file_path=str(final_path),
            file_size=int(payload.get("file_size") or final_path.stat().st_size),
            mime_type=str(payload.get("mime_type") or mimetypes.guess_type(final_path.name)[0] or "application/octet-stream"),
            uploaded_by=str(applicant_user.user_id),
            kb_id=str(payload.get("kb_id") or payload.get("kb_ref") or ""),
            kb_dataset_id=(str(payload.get("kb_dataset_id")) if payload.get("kb_dataset_id") else None),
            kb_name=(str(payload.get("kb_name")) if payload.get("kb_name") else None),
            status="pending",
        )
        try:
            doc = KnowledgeIngestionManager(deps=deps).finalize_document(
                doc=doc,
                reviewed_by=str(applicant_user.user_id),
                review_notes=f"operation_approval:{request_data['request_id']}",
            )
        except Exception as exc:
            raise OperationExecutionError(str(exc) or "document_finalize_failed", status_code=500) from exc

        audit = getattr(deps, "audit_log_store", None)
        if audit:
            audit.log_event(
                action="document_upload",
                actor=str(applicant_user.user_id),
                source="knowledge",
                doc_id=doc.doc_id,
                filename=doc.filename,
                kb_id=(doc.kb_name or doc.kb_id),
                kb_dataset_id=getattr(doc, "kb_dataset_id", None),
                kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
                meta={
                    "file_size": getattr(doc, "file_size", None),
                    "status": getattr(doc, "status", None),
                    "approval_request_id": request_data["request_id"],
                },
                **actor_fields_from_user(deps, applicant_user),
            )
        return {
            "doc_id": doc.doc_id,
            "filename": doc.filename,
            "status": doc.status,
            "kb_id": doc.kb_id,
        }


class KnowledgeFileDeleteApprovalHandler(BaseOperationApprovalHandler):
    operation_type = "knowledge_file_delete"

    async def prepare_request(self, *, request_id: str, ctx: Any, doc_id: str) -> PreparedOperationRequest:  # noqa: ARG002
        deps = ctx.deps
        snapshot = ctx.snapshot
        assert_can_delete(snapshot)
        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="document_not_found")
        assert_kb_allowed(snapshot, doc.kb_id)
        return PreparedOperationRequest(
            operation_type=self.operation_type,
            target_ref=doc.doc_id,
            target_label=doc.filename,
            summary={
                "doc_id": doc.doc_id,
                "filename": doc.filename,
                "kb_id": (doc.kb_name or doc.kb_id),
            },
            payload={
                "doc_id": doc.doc_id,
                "filename": doc.filename,
                "kb_id": doc.kb_id,
                "kb_dataset_id": getattr(doc, "kb_dataset_id", None),
                "kb_name": getattr(doc, "kb_name", None),
                "ragflow_doc_id": getattr(doc, "ragflow_doc_id", None),
                "file_path": getattr(doc, "file_path", None),
            },
        )

    def execute_request(self, *, request_data: dict, deps: Any, applicant_user: Any) -> dict:
        payload = request_data.get("payload") or {}
        doc_id = str(payload.get("doc_id") or "")
        if not doc_id:
            raise OperationExecutionError("doc_id_missing", status_code=400)
        manager = DocumentManager(deps)
        try:
            result = manager.delete_knowledge_document_trusted(
                doc_id=doc_id,
                actor_user_id=str(applicant_user.user_id),
                actor_user=applicant_user,
                approval_request_id=str(request_data["request_id"]),
            )
        except HTTPException as exc:
            code = str(exc.detail or "delete_failed")
            if code == "document_not_found":
                raise OperationExecutionError("doc_not_found_at_execution", status_code=409) from exc
            raise OperationExecutionError(code, status_code=exc.status_code) from exc
        return {
            "message": result.message,
            "ragflow_deleted": result.ragflow_deleted,
        }


class KnowledgeBaseCreateApprovalHandler(BaseOperationApprovalHandler):
    operation_type = "knowledge_base_create"

    async def prepare_request(self, *, request_id: str, ctx: Any, body: dict) -> PreparedOperationRequest:  # noqa: ARG002
        manager = getattr(ctx.deps, "knowledge_management_manager", None)
        if manager is None:
            raise HTTPException(status_code=500, detail="knowledge_management_manager_unavailable")
        try:
            payload = manager.prepare_dataset_create_payload(user=ctx.user, payload=body or {})
        except Exception as exc:
            raise HTTPException(
                status_code=int(getattr(exc, "status_code", 400) or 400),
                detail=str(exc),
            ) from exc
        name = str(payload.get("name") or "").strip()
        return PreparedOperationRequest(
            operation_type=self.operation_type,
            target_ref=name,
            target_label=name,
            summary={"name": name},
            payload=payload,
        )

    def execute_request(self, *, request_data: dict, deps: Any, applicant_user: Any) -> dict:
        payload = dict(request_data.get("payload") or {})
        try:
            created = deps.knowledge_management_manager.create_dataset(user=applicant_user, payload=payload)
        except Exception as exc:
            raise OperationExecutionError(str(exc) or "dataset_create_failed", status_code=409) from exc
        if not created:
            raise OperationExecutionError("dataset_create_failed", status_code=500)
        audit = getattr(deps, "audit_log_store", None)
        if audit:
            audit.log_event(
                action="datasets_create",
                actor=str(applicant_user.user_id),
                source="ragflow",
                kb_id=str(created.get("id") or ""),
                kb_name=str(created.get("name") or payload.get("name") or ""),
                meta={
                    "keys": sorted([k for k in payload.keys() if isinstance(k, str)])[:100],
                    "approval_request_id": request_data["request_id"],
                },
                **actor_fields_from_user(deps, applicant_user),
            )
        return {"dataset": created}


class KnowledgeBaseDeleteApprovalHandler(BaseOperationApprovalHandler):
    operation_type = "knowledge_base_delete"

    async def prepare_request(self, *, request_id: str, ctx: Any, dataset_ref: str) -> PreparedOperationRequest:  # noqa: ARG002
        manager = getattr(ctx.deps, "knowledge_management_manager", None)
        if manager is None:
            raise HTTPException(status_code=500, detail="knowledge_management_manager_unavailable")
        try:
            payload = manager.prepare_dataset_delete(user=ctx.user, dataset_ref=dataset_ref)
        except Exception as exc:
            raise HTTPException(
                status_code=int(getattr(exc, "status_code", 400) or 400),
                detail=str(exc),
            ) from exc
        dataset_id = str(payload.get("dataset_id") or dataset_ref)
        dataset_name = str(payload.get("dataset_name") or dataset_ref)
        if _dataset_local_document_count(
            ctx.deps,
            dataset_ref=str(dataset_ref or ""),
            dataset_id=dataset_id,
            dataset_name=dataset_name,
        ) > 0:
            raise HTTPException(status_code=409, detail="dataset_not_empty")
        return PreparedOperationRequest(
            operation_type=self.operation_type,
            target_ref=dataset_id,
            target_label=dataset_name,
            summary={"dataset_id": dataset_id, "dataset_name": dataset_name},
            payload=payload,
        )

    def execute_request(self, *, request_data: dict, deps: Any, applicant_user: Any) -> dict:
        payload = request_data.get("payload") or {}
        dataset_id = str(payload.get("dataset_id") or "")
        dataset_ref = str(payload.get("dataset_ref") or dataset_id or "")
        dataset_name = str(payload.get("dataset_name") or "")
        if _dataset_local_document_count(
            deps,
            dataset_ref=dataset_ref,
            dataset_id=dataset_id,
            dataset_name=dataset_name,
        ) > 0:
            raise OperationExecutionError("dataset_not_empty_at_execution", status_code=409)
        try:
            deps.knowledge_management_manager.delete_dataset(
                user=applicant_user,
                dataset_ref=dataset_id or dataset_ref,
            )
        except ValueError as exc:
            code = str(exc) or "dataset_delete_failed"
            if code == "dataset_not_empty":
                raise OperationExecutionError("dataset_not_empty_at_execution", status_code=409) from exc
            raise OperationExecutionError(code, status_code=409) from exc
        except Exception as exc:
            raise OperationExecutionError(str(exc) or "dataset_delete_failed", status_code=500) from exc
        audit = getattr(deps, "audit_log_store", None)
        if audit:
            audit.log_event(
                action="datasets_delete",
                actor=str(applicant_user.user_id),
                source="ragflow",
                kb_id=str(payload.get("dataset_id") or dataset_ref),
                kb_name=str(payload.get("dataset_name") or dataset_ref),
                meta={"approval_request_id": request_data["request_id"]},
                **actor_fields_from_user(deps, applicant_user),
            )
        return {"ok": True, "dataset_id": str(payload.get("dataset_id") or dataset_ref)}


class LegacyDocumentReviewApprovalHandler(BaseOperationApprovalHandler):
    operation_type = INTERNAL_OPERATION_TYPE_LEGACY_DOCUMENT_REVIEW

    async def prepare_request(self, *, request_id: str, ctx: Any, **kwargs) -> PreparedOperationRequest:  # noqa: ARG002
        raise HTTPException(status_code=400, detail="legacy_document_review_create_not_supported")

    def execute_request(self, *, request_data: dict, deps: Any, applicant_user: Any) -> dict:  # noqa: ARG002
        payload = request_data.get("payload") or {}
        doc_id = str(payload.get("doc_id") or "")
        if not doc_id:
            raise OperationExecutionError("legacy_review_doc_id_missing", status_code=400)

        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise OperationExecutionError("legacy_review_document_not_found", status_code=409)
        if str(getattr(doc, "status", "") or "") != "pending":
            raise OperationExecutionError("legacy_review_document_not_pending", status_code=409)

        reviewer_user_id = None
        review_notes = None
        for event in reversed(request_data.get("events") or []):
            if str(event.get("event_type") or "") != "request_approved":
                continue
            reviewer_user_id = str(event.get("actor_user_id") or "").strip() or None
            break
        for step in reversed(request_data.get("steps") or []):
            for approver in step.get("approvers") or []:
                if str(approver.get("action") or "") != "approve":
                    continue
                if reviewer_user_id and str(approver.get("approver_user_id") or "") != reviewer_user_id:
                    continue
                review_notes = approver.get("notes")
                if not reviewer_user_id:
                    reviewer_user_id = str(approver.get("approver_user_id") or "").strip() or None
                break
            if reviewer_user_id:
                break

        try:
            updated = KnowledgeIngestionManager(deps=deps).finalize_document(
                doc=doc,
                reviewed_by=str(reviewer_user_id or applicant_user.user_id),
                review_notes=str(review_notes or "").strip() or f"legacy_document_review:{request_data['request_id']}",
            )
        except Exception as exc:
            raise OperationExecutionError(str(exc) or "legacy_review_execute_failed", status_code=500) from exc

        return {
            "doc_id": updated.doc_id,
            "filename": updated.filename,
            "status": updated.status,
            "kb_id": updated.kb_id,
        }

    def reject_request(
        self,
        *,
        request_data: dict,
        deps: Any,
        actor_user: Any,
        notes: str | None,
        signature_id: str,  # noqa: ARG002
    ) -> None:
        payload = request_data.get("payload") or {}
        doc_id = str(payload.get("doc_id") or "")
        if not doc_id:
            raise OperationExecutionError("legacy_review_doc_id_missing", status_code=400)
        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise OperationExecutionError("legacy_review_document_not_found", status_code=409)
        if str(getattr(doc, "status", "") or "") != "pending":
            raise OperationExecutionError("legacy_review_document_not_pending", status_code=409)
        updated = deps.kb_store.update_document_status(
            doc_id=doc_id,
            status="rejected",
            reviewed_by=str(actor_user.user_id),
            review_notes=str(notes or "").strip() or f"legacy_document_review_rejected:{request_data['request_id']}",
        )
        if updated is None:
            raise OperationExecutionError("legacy_review_reject_failed", status_code=500)


HANDLER_REGISTRY: dict[str, BaseOperationApprovalHandler] = {
    "knowledge_file_upload": KnowledgeFileUploadApprovalHandler(),
    "knowledge_file_delete": KnowledgeFileDeleteApprovalHandler(),
    "knowledge_base_create": KnowledgeBaseCreateApprovalHandler(),
    "knowledge_base_delete": KnowledgeBaseDeleteApprovalHandler(),
    INTERNAL_OPERATION_TYPE_LEGACY_DOCUMENT_REVIEW: LegacyDocumentReviewApprovalHandler(),
}

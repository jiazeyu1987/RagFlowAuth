from fastapi import APIRouter, HTTPException, Request

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_can_review, assert_kb_allowed
from backend.app.core.signature_support import effective_review_notes, resolve_signature_service
from backend.app.core.training_support import assert_user_training_for_action
from backend.models.document import (
    BatchDocumentReviewRequest,
    BatchDocumentReviewResponse,
    DocumentResponse,
    DocumentReviewRequest,
)
from backend.services.approval import ApprovalWorkflowError, ApprovalWorkflowService, ApprovalWorkflowStore
from backend.services.electronic_signature import AuthorizedSignatureContext, ElectronicSignatureError


router = APIRouter()


def _resolve_workflow_service(deps) -> ApprovalWorkflowService:
    service = getattr(deps, "approval_workflow_service", None)
    if service is not None:
        return service
    kb_store = getattr(deps, "kb_store", None)
    db_path = getattr(kb_store, "db_path", None)
    if not db_path:
        raise HTTPException(status_code=500, detail="approval_workflow_service_unavailable")
    notification_service = getattr(deps, "notification_service", None)
    return ApprovalWorkflowService(
        store=ApprovalWorkflowStore(db_path=str(db_path)),
        notification_service=notification_service,
    )


def _to_document_response(updated_doc, approval: dict | None = None, *, signature=None) -> DocumentResponse:
    approval = approval or {}
    return DocumentResponse(
        doc_id=updated_doc.doc_id,
        filename=updated_doc.filename,
        file_size=updated_doc.file_size,
        mime_type=updated_doc.mime_type,
        uploaded_by=updated_doc.uploaded_by,
        status=updated_doc.status,
        uploaded_at_ms=updated_doc.uploaded_at_ms,
        reviewed_by=updated_doc.reviewed_by,
        reviewed_at_ms=updated_doc.reviewed_at_ms,
        review_notes=updated_doc.review_notes,
        ragflow_doc_id=updated_doc.ragflow_doc_id,
        kb_id=updated_doc.kb_id,
        approval_status=approval.get("approval_status"),
        current_step_no=approval.get("current_step_no"),
        current_step_name=approval.get("current_step_name"),
        signature_id=(getattr(signature, "signature_id", None) if signature is not None else None),
        signed_at_ms=(getattr(signature, "signed_at_ms", None) if signature is not None else None),
        logical_doc_id=getattr(updated_doc, "logical_doc_id", None),
        version_no=getattr(updated_doc, "version_no", 1),
        previous_doc_id=getattr(updated_doc, "previous_doc_id", None),
        superseded_by_doc_id=getattr(updated_doc, "superseded_by_doc_id", None),
        is_current=getattr(updated_doc, "is_current", True),
        effective_status=getattr(updated_doc, "effective_status", None),
        archived_at_ms=getattr(updated_doc, "archived_at_ms", None),
        retention_until_ms=getattr(updated_doc, "retention_until_ms", None),
        file_sha256=getattr(updated_doc, "file_sha256", None),
    )


def _doc_audit_state(doc, approval: dict | None = None) -> dict:
    data = {
        "doc_id": getattr(doc, "doc_id", None),
        "status": getattr(doc, "status", None),
        "reviewed_by": getattr(doc, "reviewed_by", None),
        "reviewed_at_ms": getattr(doc, "reviewed_at_ms", None),
        "review_notes": getattr(doc, "review_notes", None),
        "ragflow_doc_id": getattr(doc, "ragflow_doc_id", None),
        "logical_doc_id": getattr(doc, "logical_doc_id", None),
        "version_no": getattr(doc, "version_no", None),
        "previous_doc_id": getattr(doc, "previous_doc_id", None),
        "superseded_by_doc_id": getattr(doc, "superseded_by_doc_id", None),
        "is_current": getattr(doc, "is_current", None),
        "effective_status": getattr(doc, "effective_status", None),
        "archived_at_ms": getattr(doc, "archived_at_ms", None),
        "retention_until_ms": getattr(doc, "retention_until_ms", None),
        "file_sha256": getattr(doc, "file_sha256", None),
    }
    if approval:
        data.update(
            {
                "approval_status": approval.get("approval_status"),
                "current_step_no": approval.get("current_step_no"),
                "current_step_name": approval.get("current_step_name"),
            }
        )
    return data


def _reject_document_impl(
    doc_id: str,
    ctx: AuthContextDep,
    request: Request | None = None,
    review_data: DocumentReviewRequest | None = None,
    signing_context: AuthorizedSignatureContext | None = None,
) -> DocumentResponse:
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    assert_can_review(snapshot)
    assert_user_training_for_action(
        deps=deps,
        user=user,
        controlled_action="document_review",
    )

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    if doc.status != "pending":
        raise HTTPException(status_code=400, detail="文档不是待审核状态")

    workflow_service = _resolve_workflow_service(deps)
    try:
        progress = workflow_service.approval_progress(doc=doc, user=user)
    except ApprovalWorkflowError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e
    if progress.get("can_review_current_step") is not True:
        raise HTTPException(status_code=403, detail="approval_actor_not_assigned_to_step")

    before_state = _doc_audit_state(doc, approval=progress)
    signature_service = resolve_signature_service(deps)
    review_notes = effective_review_notes(review_data)
    signature_reason = review_data.signature_reason if review_data else None
    signature_meaning = review_data.signature_meaning if review_data else None
    signature_action = "document_reject"
    try:
        signing_context = signing_context or signature_service.consume_sign_token(
            user=user,
            sign_token=(review_data.sign_token if review_data else ""),
            action=signature_action,
        )
    except ElectronicSignatureError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e

    try:
        approval = workflow_service.reject_step(
            doc=doc,
            actor=ctx.payload.sub,
            actor_user=user,
            notes=review_notes,
        )
    except ApprovalWorkflowError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e
    updated_doc = deps.kb_store.update_document_status(
        doc_id=doc_id,
        status="rejected",
        reviewed_by=ctx.payload.sub,
        review_notes=review_notes,
    )
    after_state = _doc_audit_state(updated_doc, approval=approval)
    try:
        signature = signature_service.create_signature(
            signing_context=signing_context,
            user=user,
            record_type="knowledge_document_review",
            record_id=str(doc_id),
            action=signature_action,
            meaning=signature_meaning,
            reason=signature_reason,
            record_payload={
                "before": before_state,
                "after": after_state,
                "doc_id": str(updated_doc.doc_id),
                "filename": updated_doc.filename,
                "kb_id": updated_doc.kb_id,
                "approval_status": approval.get("approval_status"),
            },
        )
    except ElectronicSignatureError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e

    request_id = getattr(getattr(request, "state", None), "request_id", None) if request else None
    client_ip = getattr(getattr(request, "client", None), "host", None) if request else None
    deps.audit_log_manager.log_record_change(
        ctx=ctx,
        action=signature_action,
        source="review",
        resource_type="knowledge_document",
        resource_id=str(doc_id),
        event_type="update",
        before=before_state,
        after=after_state,
        reason=signature_reason,
        signature_id=signature.signature_id,
        request_id=request_id,
        client_ip=client_ip,
        doc_id=updated_doc.doc_id,
        filename=updated_doc.filename,
        kb_id=(getattr(updated_doc, "kb_name", None) or updated_doc.kb_id),
        kb_dataset_id=getattr(updated_doc, "kb_dataset_id", None),
        kb_name=getattr(updated_doc, "kb_name", None) or updated_doc.kb_id,
        meta={"action": "reject", "signature_meaning": signature_meaning},
    )
    return _to_document_response(updated_doc, approval=approval, signature=signature)


@router.post("/documents/batch/reject", response_model=BatchDocumentReviewResponse)
def reject_documents_batch(body: BatchDocumentReviewRequest, request: Request, ctx: AuthContextDep):
    review_data = DocumentReviewRequest(
        sign_token=body.sign_token,
        signature_meaning=body.signature_meaning,
        signature_reason=body.signature_reason,
        review_notes=body.review_notes,
    )
    succeeded_doc_ids = []
    failed_items = []
    try:
        signing_context = resolve_signature_service(ctx.deps).consume_sign_token(
            user=ctx.user,
            sign_token=body.sign_token,
            action="document_reject_batch",
        )
    except ElectronicSignatureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    for doc_id in body.doc_ids:
        try:
            _reject_document_impl(
                doc_id,
                ctx,
                request=request,
                review_data=review_data,
                signing_context=signing_context,
            )
            succeeded_doc_ids.append(doc_id)
        except HTTPException as exc:
            failed_items.append({"doc_id": doc_id, "detail": exc.detail, "status_code": exc.status_code})
        except Exception as exc:  # pragma: no cover
            failed_items.append({"doc_id": doc_id, "detail": str(exc), "status_code": 500})

    return BatchDocumentReviewResponse(
        total=len(body.doc_ids),
        success_count=len(succeeded_doc_ids),
        failed_count=len(failed_items),
        succeeded_doc_ids=succeeded_doc_ids,
        failed_items=failed_items,
    )


@router.post("/documents/{doc_id}/reject", response_model=DocumentResponse)
def reject_document(
    doc_id: str,
    request: Request,
    ctx: AuthContextDep,
    review_data: DocumentReviewRequest,
):
    return _reject_document_impl(doc_id, ctx, request=request, review_data=review_data)

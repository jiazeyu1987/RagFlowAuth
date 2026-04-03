from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from backend.app.core.authz import AuthContextDep
from backend.app.core.filename_normalize import normalize_filename_for_conflict
from backend.app.core.permission_resolver import assert_can_review, assert_kb_allowed
from backend.app.core.signature_support import effective_review_notes, resolve_signature_service
from backend.app.core.training_support import assert_user_training_for_action
from backend.models.document import DocumentOverwriteReviewRequest, DocumentResponse
from backend.services.approval import ApprovalWorkflowError, ApprovalWorkflowService, ApprovalWorkflowStore
from backend.services.electronic_signature import ElectronicSignatureError


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
        "filename": getattr(doc, "filename", None),
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


@router.post("/documents/{doc_id}/approve-overwrite", response_model=DocumentResponse)
def approve_document_overwrite(
    doc_id: str,
    request: Request,
    ctx: AuthContextDep,
    body: DocumentOverwriteReviewRequest,
):
    import logging

    logger = logging.getLogger(__name__)
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    assert_can_review(snapshot)
    assert_user_training_for_action(
        deps=deps,
        user=user,
        controlled_action="document_review",
    )

    replace_doc_id = body.replace_doc_id
    review_notes = effective_review_notes(body)
    if not replace_doc_id:
        raise HTTPException(status_code=400, detail="missing_replace_doc_id")

    new_doc = deps.kb_store.get_document(doc_id)
    if not new_doc:
        raise HTTPException(status_code=404, detail="document_not_found")
    if new_doc.status != "pending":
        raise HTTPException(status_code=400, detail="document_not_pending")
    assert_kb_allowed(snapshot, new_doc.kb_id)

    old_doc = deps.kb_store.get_document(str(replace_doc_id))
    if not old_doc:
        raise HTTPException(status_code=404, detail="replace_document_not_found")
    if old_doc.status != "approved":
        raise HTTPException(status_code=400, detail="replace_document_not_approved")

    new_norm = normalize_filename_for_conflict(new_doc.filename)
    old_norm = normalize_filename_for_conflict(old_doc.filename)
    kb_refs = {new_doc.kb_id, new_doc.kb_dataset_id, new_doc.kb_name}
    old_kb_refs = {old_doc.kb_id, old_doc.kb_dataset_id, old_doc.kb_name}
    if old_norm != new_norm or not (old_kb_refs & kb_refs):
        raise HTTPException(status_code=400, detail="replace_document_mismatch")

    if not Path(new_doc.file_path).exists():
        raise HTTPException(status_code=404, detail="new_local_file_not_found")

    workflow_service = _resolve_workflow_service(deps)
    try:
        progress = workflow_service.approval_progress(doc=new_doc, user=user)
    except ApprovalWorkflowError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e
    if progress.get("can_review_current_step") is not True:
        raise HTTPException(status_code=403, detail="approval_actor_not_assigned_to_step")

    request_id = getattr(getattr(request, "state", None), "request_id", None)
    client_ip = getattr(getattr(request, "client", None), "host", None)
    before_state = {
        "new_document": _doc_audit_state(new_doc, approval=progress),
        "old_document": _doc_audit_state(old_doc),
        "replace_doc_id": str(replace_doc_id),
    }
    signature_service = resolve_signature_service(deps)
    signature_reason = body.signature_reason
    signature_meaning = body.signature_meaning
    signature_action = "document_supersede" if bool(progress.get("is_final_step")) else "document_supersede_step"
    try:
        signing_context = signature_service.consume_sign_token(
            user=user,
            sign_token=body.sign_token,
            action=signature_action,
        )
    except ElectronicSignatureError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e

    if not bool(progress.get("is_final_step")):
        try:
            approval = workflow_service.approve_step(
                doc=new_doc,
                actor=ctx.payload.sub,
                actor_user=user,
                notes=review_notes,
                final=False,
            )
        except ApprovalWorkflowError as e:
            raise HTTPException(status_code=e.status_code, detail=e.code) from e
        after_state = {
            "new_document": _doc_audit_state(new_doc, approval=approval),
            "old_document": _doc_audit_state(old_doc),
            "replace_doc_id": str(replace_doc_id),
        }
        try:
            signature = signature_service.create_signature(
                signing_context=signing_context,
                user=user,
                record_type="knowledge_document_review",
                record_id=str(new_doc.doc_id),
                action=signature_action,
                meaning=signature_meaning,
                reason=signature_reason,
                record_payload={
                    "before": before_state,
                    "after": after_state,
                    "replace_doc_id": str(replace_doc_id),
                },
            )
        except ElectronicSignatureError as e:
            raise HTTPException(status_code=e.status_code, detail=e.code) from e
        deps.audit_log_manager.log_record_change(
            ctx=ctx,
            action=signature_action,
            source="review",
            resource_type="knowledge_document",
            resource_id=str(new_doc.doc_id),
            event_type="update",
            before=before_state,
            after=after_state,
            reason=signature_reason,
            signature_id=signature.signature_id,
            request_id=request_id,
            client_ip=client_ip,
            doc_id=new_doc.doc_id,
            filename=new_doc.filename,
            kb_id=(getattr(new_doc, "kb_name", None) or new_doc.kb_id),
            kb_dataset_id=getattr(new_doc, "kb_dataset_id", None),
            kb_name=getattr(new_doc, "kb_name", None) or new_doc.kb_id,
            meta={
                "replace_doc_id": str(replace_doc_id),
                "action": "supersede_step",
                "signature_meaning": signature_meaning,
            },
        )
        return _to_document_response(new_doc, approval=approval, signature=signature)

    # Final step: execute replacement flow.
    if not old_doc.ragflow_doc_id:
        deps.deletion_log_store.log_deletion(
            doc_id=old_doc.doc_id,
            filename=old_doc.filename,
            kb_id=(old_doc.kb_name or old_doc.kb_id),
            deleted_by=ctx.payload.sub,
            kb_dataset_id=old_doc.kb_dataset_id,
            kb_name=old_doc.kb_name,
            original_uploader=old_doc.uploaded_by,
            original_reviewer=old_doc.reviewed_by,
            ragflow_doc_id=old_doc.ragflow_doc_id,
            action="overwrite",
            ragflow_deleted=0,
            ragflow_delete_error="missing_ragflow_doc_id",
        )
        raise HTTPException(status_code=500, detail="replace_document_missing_ragflow_doc_id")

    dataset_ref = old_doc.kb_dataset_id or old_doc.kb_id or (old_doc.kb_name or "")
    rag_ok = False
    rag_err = None
    try:
        rag_ok = bool(deps.ragflow_service.delete_document(old_doc.ragflow_doc_id, dataset_name=dataset_ref))
        if not rag_ok:
            rag_err = "ragflow_delete_failed"
    except Exception as e:
        rag_ok = False
        rag_err = str(e)

    deps.deletion_log_store.log_deletion(
        doc_id=old_doc.doc_id,
        filename=old_doc.filename,
        kb_id=(old_doc.kb_name or old_doc.kb_id),
        deleted_by=ctx.payload.sub,
        kb_dataset_id=old_doc.kb_dataset_id,
        kb_name=old_doc.kb_name,
        original_uploader=old_doc.uploaded_by,
        original_reviewer=old_doc.reviewed_by,
        ragflow_doc_id=old_doc.ragflow_doc_id,
        action="overwrite",
        ragflow_deleted=1 if rag_ok else 0,
        ragflow_delete_error=None if rag_ok else rag_err,
    )
    if not rag_ok:
        raise HTTPException(status_code=500, detail=f"replace_delete_failed:{rag_err}")

    with open(new_doc.file_path, "rb") as f:
        file_content = f.read()

    ragflow_doc_id = deps.ragflow_service.upload_document_blob(
        file_filename=new_doc.filename,
        file_content=file_content,
        kb_id=new_doc.kb_id,
    )
    if not ragflow_doc_id:
        raise HTTPException(status_code=500, detail="ragflow_upload_failed")

    dataset_ref = new_doc.kb_dataset_id or new_doc.kb_id or (new_doc.kb_name or "")
    if ragflow_doc_id and ragflow_doc_id != "uploaded":
        try:
            ok = deps.ragflow_service.parse_document(dataset_ref=dataset_ref, document_id=ragflow_doc_id)
            if not ok:
                logger.warning(
                    "[APPROVE-OVERWRITE] Parse trigger failed: doc_id=%s ragflow_doc_id=%s dataset_ref=%s",
                    new_doc.doc_id,
                    ragflow_doc_id,
                    dataset_ref,
                )
        except Exception as e:
            logger.warning(
                "[APPROVE-OVERWRITE] Parse trigger exception: doc_id=%s ragflow_doc_id=%s dataset_ref=%s err=%s",
                new_doc.doc_id,
                ragflow_doc_id,
                dataset_ref,
                e,
            )
    else:
        logger.warning("[APPROVE-OVERWRITE] Skip parse trigger: ragflow_doc_id is not available (%s)", ragflow_doc_id)

    try:
        approval = workflow_service.approve_step(
            doc=new_doc,
            actor=ctx.payload.sub,
            actor_user=user,
            notes=review_notes,
            final=True,
        )
    except ApprovalWorkflowError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e
    updated_doc = deps.kb_store.update_document_status(
        doc_id=new_doc.doc_id,
        status="approved",
        reviewed_by=ctx.payload.sub,
        review_notes=review_notes,
        ragflow_doc_id=ragflow_doc_id,
    )
    try:
        _, updated_doc = deps.kb_store.apply_version_replacement(
            old_doc_id=old_doc.doc_id,
            new_doc_id=new_doc.doc_id,
            effective_status="approved",
            retention_until_ms=getattr(old_doc, "retention_until_ms", None),
        )
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"version_chain_update_failed:{e}") from e
    superseded_old_doc = deps.kb_store.get_document(old_doc.doc_id)
    after_state = {
        "new_document": _doc_audit_state(updated_doc, approval=approval),
        "old_document": _doc_audit_state(superseded_old_doc),
        "replaced_doc_id": old_doc.doc_id,
    }
    try:
        signature = signature_service.create_signature(
            signing_context=signing_context,
            user=user,
            record_type="knowledge_document_review",
            record_id=str(updated_doc.doc_id),
            action=signature_action,
            meaning=signature_meaning,
            reason=signature_reason,
            record_payload={
                "before": before_state,
                "after": after_state,
                "replace_doc_id": str(old_doc.doc_id),
                "new_ragflow_doc_id": ragflow_doc_id,
            },
        )
    except ElectronicSignatureError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e

    deps.audit_log_manager.log_record_change(
        ctx=ctx,
        action=signature_action,
        source="review",
        resource_type="knowledge_document",
        resource_id=str(updated_doc.doc_id),
        event_type="supersede",
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
        meta={"replace_doc_id": old_doc.doc_id, "signature_meaning": signature_meaning},
    )

    return _to_document_response(updated_doc, approval=approval, signature=signature)

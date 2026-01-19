from fastapi import APIRouter, HTTPException
from pathlib import Path

from backend.app.core.authz import AuthContextDep
from backend.app.core.filename_normalize import normalize_filename_for_conflict
from backend.app.core.permission_resolver import assert_can_review, assert_kb_allowed
from backend.models.document import DocumentResponse, DocumentReviewRequest


router = APIRouter()


@router.get("/documents/{doc_id}/conflict")
async def get_document_conflict(doc_id: str, ctx: AuthContextDep) -> dict:
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    if doc.status != "pending":
        return {"conflict": False}

    normalized = normalize_filename_for_conflict(doc.filename)
    kb_refs = [r for r in {doc.kb_id, doc.kb_dataset_id, doc.kb_name} if r]

    approved = deps.kb_store.list_documents(status="approved", kb_refs=kb_refs, limit=2000)
    existing = None
    for d in approved:
        if d.doc_id == doc.doc_id:
            continue
        if normalize_filename_for_conflict(d.filename) == normalized:
            existing = d
            break

    if not existing:
        return {"conflict": False}

    usernames = {}
    try:
        usernames = deps.user_store.get_usernames_by_ids({existing.uploaded_by, existing.reviewed_by} - {None, ""})
    except Exception:
        usernames = {}

    return {
        "conflict": True,
        "normalized_name": normalized,
        "existing": {
            "doc_id": existing.doc_id,
            "filename": existing.filename,
            "uploaded_by": existing.uploaded_by,
            "uploaded_by_name": usernames.get(existing.uploaded_by) if existing.uploaded_by else None,
            "uploaded_at_ms": existing.uploaded_at_ms,
            "reviewed_by": existing.reviewed_by,
            "reviewed_by_name": usernames.get(existing.reviewed_by) if existing.reviewed_by else None,
            "reviewed_at_ms": existing.reviewed_at_ms,
            "ragflow_doc_id": existing.ragflow_doc_id,
            "kb_id": existing.kb_name or existing.kb_id,
        },
    }


@router.post("/documents/{doc_id}/approve", response_model=DocumentResponse)
async def approve_document(
    doc_id: str,
    ctx: AuthContextDep,
    review_data: DocumentReviewRequest = None,
):
    import logging
    logger = logging.getLogger(__name__)

    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    logger.info(f"[APPROVE] User {user.username} approving doc {doc_id}")

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        logger.error(f"[APPROVE] Document not found: {doc_id}")
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    if doc.status != "pending":
        logger.error(f"[APPROVE] Document status is not pending: {doc.status}")
        raise HTTPException(status_code=400, detail="文档不是待审核状态")

    try:
        if not Path(doc.file_path).exists():
            logger.error(f"[APPROVE] Local file not found: {doc.file_path}")
            raise HTTPException(status_code=404, detail="本地文件不存在")

        with open(doc.file_path, "rb") as f:
            file_content = f.read()

        ragflow_doc_id = deps.ragflow_service.upload_document_blob(
            file_filename=doc.filename,
            file_content=file_content,
            kb_id=doc.kb_id,
        )

        if not ragflow_doc_id:
            raise HTTPException(status_code=500, detail="上传到RAGFlow失败")

        updated_doc = deps.kb_store.update_document_status(
            doc_id=doc_id,
            status="approved",
            reviewed_by=ctx.payload.sub,
            review_notes=review_data.review_notes if review_data else None,
            ragflow_doc_id=ragflow_doc_id,
        )

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
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[APPROVE] Exception during approval: {e}")
        raise HTTPException(status_code=500, detail=f"审核失败: {str(e)}")


@router.post("/documents/{doc_id}/approve-overwrite", response_model=DocumentResponse)
async def approve_document_overwrite(doc_id: str, ctx: AuthContextDep, body: dict | None = None):
    import logging

    logger = logging.getLogger(__name__)
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    replace_doc_id = (body or {}).get("replace_doc_id")
    review_notes = (body or {}).get("review_notes")
    if not replace_doc_id:
        raise HTTPException(status_code=400, detail="缺少 replace_doc_id")

    new_doc = deps.kb_store.get_document(doc_id)
    if not new_doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if new_doc.status != "pending":
        raise HTTPException(status_code=400, detail="文档不是待审核状态")
    assert_kb_allowed(snapshot, new_doc.kb_id)

    old_doc = deps.kb_store.get_document(str(replace_doc_id))
    if not old_doc:
        raise HTTPException(status_code=404, detail="旧文档不存在")
    if old_doc.status != "approved":
        raise HTTPException(status_code=400, detail="旧文档不是已通过状态")

    new_norm = normalize_filename_for_conflict(new_doc.filename)
    old_norm = normalize_filename_for_conflict(old_doc.filename)
    kb_refs = {new_doc.kb_id, new_doc.kb_dataset_id, new_doc.kb_name}
    if old_norm != new_norm or not ({old_doc.kb_id, old_doc.kb_dataset_id, old_doc.kb_name} & kb_refs):
        raise HTTPException(status_code=400, detail="旧文档与新文档不匹配，无法覆盖")

    if not Path(new_doc.file_path).exists():
        raise HTTPException(status_code=404, detail="本地文件不存在")

    # 1) Delete old from RAGFlow first (must succeed)
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
            ragflow_delete_error="旧文档缺少 ragflow_doc_id，无法删除 RAGFlow 内容",
        )
        raise HTTPException(status_code=500, detail="旧文档缺少 ragflow_doc_id，无法覆盖（请联系管理员）")

    dataset_ref = old_doc.kb_dataset_id or old_doc.kb_id or (old_doc.kb_name or "")
    rag_ok = False
    rag_err = None
    try:
        rag_ok = bool(deps.ragflow_service.delete_document(old_doc.ragflow_doc_id, dataset_name=dataset_ref))
        if not rag_ok:
            rag_err = "RAGFlow 删除失败"
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
        raise HTTPException(status_code=500, detail=f"无法从 RAGFlow 删除旧文件，已记录：{rag_err}")

    # 2) Delete old local record + file
    try:
        if Path(old_doc.file_path).exists():
            Path(old_doc.file_path).unlink()
    except Exception:
        logger.warning("Failed to delete old local file: %s", old_doc.file_path)
    deps.kb_store.delete_document(old_doc.doc_id)

    # 3) Upload new to RAGFlow and approve
    with open(new_doc.file_path, "rb") as f:
        file_content = f.read()

    ragflow_doc_id = deps.ragflow_service.upload_document_blob(
        file_filename=new_doc.filename,
        file_content=file_content,
        kb_id=new_doc.kb_id,
    )
    if not ragflow_doc_id:
        raise HTTPException(status_code=500, detail="上传到RAGFlow失败")

    updated_doc = deps.kb_store.update_document_status(
        doc_id=new_doc.doc_id,
        status="approved",
        reviewed_by=ctx.payload.sub,
        review_notes=review_notes,
        ragflow_doc_id=ragflow_doc_id,
    )

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
    )


@router.post("/documents/{doc_id}/reject", response_model=DocumentResponse)
async def reject_document(
    doc_id: str,
    ctx: AuthContextDep,
    review_data: DocumentReviewRequest = None,
):
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    if doc.status != "pending":
        raise HTTPException(status_code=400, detail="文档不是待审核状态")

    updated_doc = deps.kb_store.update_document_status(
        doc_id=doc_id,
        status="rejected",
        reviewed_by=ctx.payload.sub,
        review_notes=review_data.review_notes if review_data else None,
    )

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
    )

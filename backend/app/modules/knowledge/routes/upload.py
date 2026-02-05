from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import (
    assert_can_upload,
    assert_kb_allowed,
)
from backend.models.document import DocumentResponse
from backend.services.documents.document_manager import DocumentManager


router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    request: Request,
    ctx: AuthContextDep,
    file: UploadFile = File(...),
):
    """
    上传文档到本地存储（pending状态）
    基于权限组检查上传权限
    """
    import logging

    logger = logging.getLogger(__name__)

    kb_ref = request.query_params.get("kb_id", "展厅")

    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    kb_info = resolve_kb_ref(deps, kb_ref)
    assert_can_upload(snapshot)
    assert_kb_allowed(snapshot, kb_ref)

    logger.info(f"[UPLOAD] User {user.username} uploading to kb_id={kb_ref}")
    mgr = DocumentManager(deps)
    doc = await mgr.stage_upload_knowledge(kb_ref=kb_ref, upload_file=file, ctx=ctx)

    logger.info(
        "[UPLOAD] Created local doc record: doc_id=%s filename=%s kb_id=%s status=%s uploaded_by=%s",
        doc.doc_id,
        doc.filename,
        doc.kb_id,
        doc.status,
        ctx.payload.sub,
    )

    return DocumentResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        uploaded_by=doc.uploaded_by,
        status=doc.status,
        uploaded_at_ms=doc.uploaded_at_ms,
        reviewed_by=doc.reviewed_by,
        reviewed_at_ms=doc.reviewed_at_ms,
        review_notes=doc.review_notes,
        ragflow_doc_id=doc.ragflow_doc_id,
        kb_id=(doc.kb_name or doc.kb_id),
    )

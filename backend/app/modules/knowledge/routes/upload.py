from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import (
    assert_can_upload,
    assert_kb_allowed,
)
from backend.models.document import DocumentResponse
from backend.services.documents.document_manager import DocumentManager
from backend.services.knowledge_ingestion import KnowledgeIngestionError


router = APIRouter()


def _get_allowed_extensions_payload(ctx: AuthContextDep) -> dict:
    settings_obj = ctx.deps.upload_settings_store.get()
    return {
        "allowed_extensions": settings_obj.allowed_extensions,
        "updated_at_ms": settings_obj.updated_at_ms,
    }


@router.get("/settings/allowed-extensions")
def get_allowed_extensions(ctx: AuthContextDep):
    return _get_allowed_extensions_payload(ctx)


@router.put("/settings/allowed-extensions")
def update_allowed_extensions(ctx: AuthContextDep, body: dict):
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")
    extensions = body.get("allowed_extensions")
    try:
        ctx.deps.upload_settings_store.update_allowed_extensions(extensions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _get_allowed_extensions_payload(ctx)


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
    ingestion_manager = getattr(deps, "knowledge_ingestion_manager", None)
    if ingestion_manager is not None:
        try:
            doc = await ingestion_manager.stage_upload_knowledge(kb_ref=kb_ref, upload_file=file, ctx=ctx)
        except KnowledgeIngestionError as e:
            raise HTTPException(status_code=e.status_code, detail=e.code) from e
    else:
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

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
import uuid
import mimetypes
from pathlib import Path

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.paths import resolve_repo_path
from backend.app.core.permission_resolver import (
    assert_can_upload,
    assert_kb_allowed,
)
from backend.models.document import DocumentResponse
from backend.app.core.config import settings


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

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过限制")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的文件类型")

    uploads_dir = resolve_repo_path(settings.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = uploads_dir / unique_filename

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info("[UPLOAD] Saved file to: %s", file_path)

    guessed_mime, _ = mimetypes.guess_type(file.filename)
    mime_type = (file.content_type or guessed_mime or "application/octet-stream").strip()
    if file_ext in {".txt", ".ini", ".log"}:
        mime_type = "text/plain; charset=utf-8"
    elif file_ext in {".md", ".markdown"}:
        mime_type = "text/markdown; charset=utf-8"

    doc = deps.kb_store.create_document(
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=mime_type,
        uploaded_by=ctx.payload.sub,
        kb_id=(kb_info.dataset_id or kb_ref),
        kb_dataset_id=kb_info.dataset_id,
        kb_name=(kb_info.name or kb_ref),
        status="pending",
    )

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


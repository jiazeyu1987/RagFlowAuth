from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, Response
from typing import Optional
import os
import uuid
import zipfile
import io
from pathlib import Path

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.paths import resolve_backend_path
from backend.app.core.permission_resolver import (
    ResourceScope,
    assert_can_delete,
    assert_can_download,
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

    # Get kb_id from query parameter (dataset id or name)
    kb_ref = request.query_params.get("kb_id", "展厅")

    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    kb_info = resolve_kb_ref(deps, kb_ref)
    assert_can_upload(snapshot)
    assert_kb_allowed(snapshot, kb_ref)

    logger.info(f"[UPLOAD] User {user.username} uploading to kb_id={kb_ref}")

    # Validate file size
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过限制")

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的文件类型")

    # 存储到本地
    uploads_dir = resolve_backend_path(settings.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = uploads_dir / unique_filename

    # 写入文件
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info("[UPLOAD] Saved file to: %s", file_path)

    # 5. 创建本地记录（pending状态）
    doc = deps.kb_store.create_document(
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=ctx.payload.sub,
        kb_id=(kb_info.dataset_id or kb_ref),
        kb_dataset_id=kb_info.dataset_id,
        kb_name=(kb_info.name or kb_ref),
        status="pending"  # 关键修改：pending状态
    )

    # ========== BACKEND STEP 3: Upload Complete ==========
    logger.info(
        "[UPLOAD] Created local doc record: doc_id=%s filename=%s kb_id=%s status=%s uploaded_by=%s",
        doc.doc_id,
        doc.filename,
        doc.kb_id,
        doc.status,
        ctx.payload.sub,
    )
    logger.info("=" * 80)

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


@router.get("/documents")
async def list_documents(
    ctx: AuthContextDep,
    status: Optional[str] = None,
    kb_id: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    limit: int = 100,
):
    """
    列出文档，带可选过滤器

    权限规则：
    - 管理员：可以看到所有文档
    - 其他角色：只能看到 resolver 允许的知识库文档
    """
    import logging
    logger = logging.getLogger(__name__)

    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    logger.info(f"[LIST DOCS] User: {user.username}, role: {user.role}, kb_id: {kb_id}, status: {status}")
    try:
        perm_logger.info(
            "[PERMDBG] /api/knowledge/documents user=%s role=%s kb_scope=%s kb_refs=%s request_kb_id=%s",
            user.username,
            user.role,
            snapshot.kb_scope,
            sorted(list(snapshot.kb_names))[:50],
            kb_id,
        )
    except Exception:
        pass

    if snapshot.kb_scope == ResourceScope.NONE:
        docs = []
    else:
        if kb_id:
            assert_kb_allowed(snapshot, kb_id)
            kb_info = resolve_kb_ref(deps, kb_id)
            docs = deps.kb_store.list_documents(
                status=status,
                kb_refs=list(kb_info.variants),
                uploaded_by=uploaded_by,
                limit=limit,
            )
        else:
            docs = deps.kb_store.list_documents(status=status, kb_id=None, uploaded_by=uploaded_by, limit=limit)
            before = len(docs)
            if snapshot.kb_scope != ResourceScope.ALL:
                docs = [
                    d
                    for d in docs
                    if (d.kb_id in snapshot.kb_names)
                    or (d.kb_dataset_id is not None and d.kb_dataset_id in snapshot.kb_names)
                    or (d.kb_name is not None and d.kb_name in snapshot.kb_names)
                ]
            try:
                perm_logger.info(
                    "[PERMDBG] /api/knowledge/documents filtered %s -> %s",
                    before,
                    len(docs),
                )
            except Exception:
                pass

    logger.info(f"[LIST DOCS] Found {len(docs)} documents")

    return {
        "documents": [
            {
                "doc_id": d.doc_id,
                "filename": d.filename,
                "file_size": d.file_size,
                "mime_type": d.mime_type,
                "uploaded_by": d.uploaded_by,
                "status": d.status,
                "uploaded_at_ms": d.uploaded_at_ms,
                "reviewed_by": d.reviewed_by,
                "reviewed_at_ms": d.reviewed_at_ms,
                "review_notes": d.review_notes,
                "ragflow_doc_id": d.ragflow_doc_id,
                "kb_id": (d.kb_name or d.kb_id),
            }
            for d in docs
        ],
        "count": len(docs)
    }


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    ctx: AuthContextDep,
):
    """Get document details"""
    deps = ctx.deps
    snapshot = ctx.snapshot
    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    return {
        "doc_id": doc.doc_id,
        "filename": doc.filename,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "uploaded_by": doc.uploaded_by,
        "status": doc.status,
        "uploaded_at_ms": doc.uploaded_at_ms,
        "reviewed_by": doc.reviewed_by,
        "reviewed_at_ms": doc.reviewed_at_ms,
        "review_notes": doc.review_notes,
        "ragflow_doc_id": doc.ragflow_doc_id,
        "kb_id": (doc.kb_name or doc.kb_id),
    }


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    ctx: AuthContextDep,
):
    """Download document file"""
    import logging
    logger = logging.getLogger(__name__)
    perm_logger = logging.getLogger("uvicorn.error")

    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    assert_can_download(snapshot)

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    # 记录下载日志
    deps.download_log_store.log_download(
        doc_id=doc.doc_id,
        filename=doc.filename,
        kb_id=(doc.kb_name or doc.kb_id),
        downloaded_by=ctx.payload.sub,
        kb_dataset_id=doc.kb_dataset_id,
        kb_name=doc.kb_name,
    )
    logger.info(f"[DOWNLOAD] Document {doc_id} ({doc.filename}) downloaded by {ctx.payload.sub}")

    return FileResponse(
        path=doc.file_path,
        filename=doc.filename,
        media_type=doc.mime_type
    )


@router.get("/stats")
async def get_stats(
    ctx: AuthContextDep,
):
    """Get document statistics"""
    deps = ctx.deps
    snapshot = ctx.snapshot
    if snapshot.is_admin:
        total = deps.kb_store.count_documents()
        pending = deps.kb_store.count_documents(status="pending")
        approved = deps.kb_store.count_documents(status="approved")
        rejected = deps.kb_store.count_documents(status="rejected")
    elif snapshot.kb_scope == ResourceScope.NONE:
        total = 0
        pending = 0
        approved = 0
        rejected = 0
    else:
        kb_ids = list(snapshot.kb_names)
        total = deps.kb_store.count_documents(kb_ids=kb_ids)
        pending = deps.kb_store.count_documents(status="pending", kb_ids=kb_ids)
        approved = deps.kb_store.count_documents(status="approved", kb_ids=kb_ids)
        rejected = deps.kb_store.count_documents(status="rejected", kb_ids=kb_ids)

    return {
        "total_documents": total,
        "pending_documents": pending,
        "approved_documents": approved,
        "rejected_documents": rejected,
    }


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    ctx: AuthContextDep,
):
    """Delete document (based on permission group)"""
    import logging
    logger = logging.getLogger(__name__)

    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_delete(snapshot)

    logger.info(f"[DELETE] delete_document() called, doc_id: {doc_id}, deleted_by: {ctx.payload.sub}")

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        logger.error(f"[DELETE] Document not found: {doc_id}")
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    # 记录删除操作
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
    )
    logger.info("[DELETE] Deletion log saved")

    # Delete file
    if os.path.exists(doc.file_path):
        logger.info(f"[DELETE] Deleting file: {doc.file_path}")
        os.remove(doc.file_path)
        logger.info("[DELETE] File deleted successfully")
    else:
        logger.warning(f"[DELETE] File not found: {doc.file_path}")

    # Delete from database
    logger.info("[DELETE] Deleting from database...")
    deps.kb_store.delete_document(doc_id)
    logger.info("[DELETE] Database record deleted")

    logger.info("[DELETE] Delete operation completed successfully")
    logger.info("=" * 80)

    return {"message": "文档已删除"}


@router.get("/deletions")
async def list_deletions(
    ctx: AuthContextDep,
    kb_id: Optional[str] = None,
    limit: int = 100,
):
    """
    获取删除记录列表

    权限规则：
    - 管理员：可以看到所有删除记录
    - 其他角色：只能看到自己的删除记录（并受 KB 可见范围限制）
    """
    deps = ctx.deps
    snapshot = ctx.snapshot
    kb_refs = None
    if kb_id:
        assert_kb_allowed(snapshot, kb_id)
        kb_refs = list(resolve_kb_ref(deps, kb_id).variants)

    deleted_by = None if snapshot.is_admin else ctx.payload.sub
    deletions = deps.deletion_log_store.list_deletions(kb_refs=kb_refs, deleted_by=deleted_by, limit=limit)

    return {
        "deletions": [
            {
                "id": d.id,
                "doc_id": d.doc_id,
                "filename": d.filename,
                "kb_id": (d.kb_name or d.kb_id),
                "deleted_by": d.deleted_by,
                "deleted_at_ms": d.deleted_at_ms,
                "original_uploader": d.original_uploader,
                "original_reviewer": d.original_reviewer,
                "ragflow_doc_id": d.ragflow_doc_id,
            }
            for d in deletions
        ],
        "count": len(deletions)
    }


@router.post("/documents/batch/download")
async def batch_download_documents(
    request: Request,
    body: dict,
    ctx: AuthContextDep,
):
    """
    批量下载文档（打包成ZIP）
    """
    import logging
    logger = logging.getLogger(__name__)

    deps = ctx.deps
    doc_ids = body.get("doc_ids", [])
    logger.info(f"[BATCH DOWNLOAD] Request to download {len(doc_ids)} documents")
    logger.info(f"[BATCH DOWNLOAD] User: {ctx.payload.sub}")

    snapshot = ctx.snapshot
    assert_can_download(snapshot)

    # 获取文档（并检查 KB 可见）
    valid_docs = []
    for doc_id in doc_ids:
        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            logger.warning(f"[BATCH DOWNLOAD] Document not found: {doc_id}")
            continue
        try:
            assert_kb_allowed(snapshot, doc.kb_id)
        except HTTPException:
            logger.warning(f"[BATCH DOWNLOAD] No access to doc {doc_id} kb_id={doc.kb_id}")
            continue

        # 检查文件是否存在
        if not os.path.exists(doc.file_path):
            logger.warning(f"[BATCH DOWNLOAD] File not found: {doc.file_path}")
            continue

        valid_docs.append(doc)

    if len(valid_docs) == 0:
        raise HTTPException(status_code=404, detail="没有找到可下载的文档")

    logger.info(f"[BATCH DOWNLOAD] Found {len(valid_docs)} valid documents for download")

    # 创建ZIP文件（在内存中）
    import time
    zip_buffer = io.BytesIO()
    created_at_ms = int(time.time() * 1000)

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for doc in valid_docs:
            # 添加文件到ZIP，使用原始文件名
            # 如果文件名重复，添加序号
            zip_name = doc.filename
            counter = 1
            while zip_name in [f.filename for f in valid_docs if f.filename != doc.filename]:
                name, ext = os.path.splitext(doc.filename)
                zip_name = f"{name}_{counter}{ext}"
                counter += 1

            try:
                zip_file.write(doc.file_path, zip_name)
                logger.info(f"[BATCH DOWNLOAD] Added to ZIP: {zip_name}")
            except Exception as e:
                logger.error(f"[BATCH DOWNLOAD] Failed to add {doc.filename} to ZIP: {e}")
                continue

    zip_buffer.seek(0)

    # 生成ZIP文件名
    zip_filename = f"documents_{created_at_ms}.zip"

    # 记录下载日志
    for doc in valid_docs:
        deps.download_log_store.log_download(
            doc_id=doc.doc_id,
            filename=doc.filename,
            kb_id=doc.kb_id,
            downloaded_by=ctx.payload.sub,
            is_batch=True,
            kb_dataset_id=doc.kb_dataset_id,
            kb_name=doc.kb_name,
        )

    logger.info(f"[BATCH DOWNLOAD] ZIP file created: {zip_filename} with {len(valid_docs)} files")

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"'
        }
    )

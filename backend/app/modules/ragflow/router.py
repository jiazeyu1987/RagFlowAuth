import logging

from fastapi import APIRouter, HTTPException, Request, Response as FastAPIResponse
from fastapi.responses import Response
from typing import Optional

from backend.app.core.authz import AuthContextDep
from backend.app.core.datasets import list_accessible_datasets
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permdbg import permdbg
from backend.app.core.permission_resolver import (
    assert_can_delete,
    assert_can_download,
    assert_kb_allowed,
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/datasets")
async def list_datasets(
    ctx: AuthContextDep,
    response: FastAPIResponse,
):
    """
    列出RAGFlow数据集（基于权限组过滤）

    权限规则：
    - 管理员：可以看到所有数据集
    - 其他角色：根据权限组的accessible_kbs配置
    """
    deps = ctx.deps
    snapshot = ctx.snapshot

    # Compatibility: legacy endpoint. Prefer `/api/datasets`.
    response.headers["Deprecation"] = "true"
    response.headers["X-Replaced-By"] = "/api/datasets"

    datasets = list_accessible_datasets(deps, snapshot)
    filtered = datasets
    try:
        permdbg(
            "ragflow.datasets.deprecated",
            user=ctx.user.username,
            role=ctx.user.role,
            kb_scope=snapshot.kb_scope,
            kb_refs=sorted(list(snapshot.kb_names))[:50],
            datasets=[d.get("name") for d in filtered[:50] if isinstance(d, dict)],
        )
    except Exception:
        pass
    return {"datasets": filtered}


@router.get("/documents")
async def list_ragflow_documents(
    ctx: AuthContextDep,
    dataset_name: str = "展厅",
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_kb_allowed(snapshot, dataset_name)
    documents = deps.ragflow_service.list_documents(dataset_name)
    return {"documents": documents, "dataset": dataset_name}


@router.get("/documents/{doc_id}/status")
async def get_document_status(
    doc_id: str,
    ctx: AuthContextDep,
    dataset_name: str = "展厅",
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_kb_allowed(snapshot, dataset_name)
    status = deps.ragflow_service.get_document_status(doc_id, dataset_name)
    if status is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"doc_id": doc_id, "status": status}


@router.get("/documents/{doc_id}")
async def get_document_detail(
    doc_id: str,
    ctx: AuthContextDep,
    dataset_name: str = "展厅",
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_kb_allowed(snapshot, dataset_name)
    detail = deps.ragflow_service.get_document_detail(doc_id, dataset_name)
    if detail is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return detail


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    ctx: AuthContextDep,
    dataset: str = "展厅",
    filename: str = None,
):
    import urllib.parse

    logger.info("[DOWNLOAD] doc_id=%s dataset=%s user=%s", doc_id, dataset, ctx.payload.sub)

    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_download(snapshot)
    assert_kb_allowed(snapshot, dataset)
    kb_info = resolve_kb_ref(deps, dataset)

    try:
        file_content, ragflow_filename = deps.ragflow_service.download_document(doc_id, dataset)

        if file_content is None:
            logger.error(f"[DOWNLOAD] Failed to download document {doc_id} from RAGFlow")
            raise HTTPException(status_code=404, detail="文档不存在或下载失败")

        deps.download_log_store.log_download(
            doc_id=doc_id,
            filename=ragflow_filename or f"document_{doc_id}",
            kb_id=(kb_info.dataset_id or dataset),
            downloaded_by=ctx.payload.sub,
            ragflow_doc_id=doc_id,
            is_batch=False,
            kb_dataset_id=kb_info.dataset_id,
            kb_name=(kb_info.name or dataset),
        )

        final_filename = filename or ragflow_filename or f"document_{doc_id}"

        try:
            final_filename.encode("ascii")
            content_disposition = f'attachment; filename="{final_filename}"'
        except UnicodeEncodeError:
            ascii_filename = final_filename.encode("ascii", "replace").decode("ascii")
            encoded_filename = urllib.parse.quote(final_filename)
            content_disposition = f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"

        return Response(
            content=file_content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": content_disposition},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[DOWNLOAD] Exception during download: %s", e)
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.get("/documents/{doc_id}/preview")
async def preview_document(
    doc_id: str,
    ctx: AuthContextDep,
    dataset: str = "展厅",
):
    import base64
    from pathlib import Path

    logger.info("[PREVIEW] doc_id=%s dataset=%s user=%s", doc_id, dataset, ctx.payload.sub)

    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_download(snapshot)
    assert_kb_allowed(snapshot, dataset)

    try:
        file_content, filename = deps.ragflow_service.download_document(doc_id, dataset)

        if file_content is None:
            logger.error(f"[PREVIEW] Failed to download document {doc_id}")
            raise HTTPException(status_code=404, detail="文档不存在")

        file_ext = Path(filename).suffix.lower() if filename else ""

        text_extensions = [".txt", ".md", ".csv", ".json", ".xml", ".log", ".svg", ".html", ".css", ".js"]
        image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]

        if file_ext in text_extensions:
            try:
                text_content = file_content.decode("utf-8")
                return {"type": "text", "filename": filename, "content": text_content}
            except UnicodeDecodeError:
                try:
                    text_content = file_content.decode("gbk")
                    return {"type": "text", "filename": filename, "content": text_content}
                except Exception:
                    logger.error("[PREVIEW] Failed to decode text file")
                    raise HTTPException(status_code=400, detail="无法解码文本文件")

        if file_ext in image_extensions:
            base64_image = base64.b64encode(file_content).decode("utf-8")
            image_type = file_ext[1:]
            return {"type": "image", "filename": filename, "content": base64_image, "image_type": image_type}

        if file_ext == ".pdf":
            base64_pdf = base64.b64encode(file_content).decode("utf-8")
            return {"type": "pdf", "filename": filename, "content": base64_pdf}

        return {"type": "unsupported", "filename": filename, "message": f"不支持的文件类型: {file_ext}，请下载后查看"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[PREVIEW] Exception: %s", e)
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")


@router.delete("/documents/{doc_id}")
async def delete_ragflow_document(
    doc_id: str,
    ctx: AuthContextDep,
    dataset_name: str = "展厅",
):
    logger.info("[DELETE] doc_id=%s dataset=%s user=%s", doc_id, dataset_name, ctx.payload.sub)

    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_delete(snapshot)
    assert_kb_allowed(snapshot, dataset_name)

    kb_info = resolve_kb_ref(deps, dataset_name)
    local_doc = deps.kb_store.get_document_by_ragflow_id(doc_id, dataset_name, kb_refs=list(kb_info.variants))

    success = deps.ragflow_service.delete_document(doc_id, dataset_name)
    if not success:
        logger.error(f"[DELETE RAGFLOW] Failed to delete from RAGFlow: {doc_id}")
        raise HTTPException(status_code=404, detail="文档不存在或删除失败")

    if local_doc:
        deps.deletion_log_store.log_deletion(
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

        import os
        if os.path.exists(local_doc.file_path):
            os.remove(local_doc.file_path)

        deps.kb_store.delete_document(local_doc.doc_id)
    else:
        deps.deletion_log_store.log_deletion(
            doc_id=doc_id,
            filename=f"RAGFlow文档({doc_id[:8]}...)",
            kb_id=(kb_info.dataset_id or dataset_name),
            deleted_by=ctx.payload.sub,
            kb_dataset_id=kb_info.dataset_id,
            kb_name=(kb_info.name or dataset_name),
            original_uploader=None,
            original_reviewer=None,
            ragflow_doc_id=doc_id,
        )

    return {"message": "文档已从RAGFlow删除"}


@router.post("/documents/batch/download")
async def batch_download_documents(
    request: Request,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    data = await request.json()
    documents_info = data.get("documents", [])
    logger.info("[BATCH DOWNLOAD] count=%s user=%s", len(documents_info), ctx.payload.sub)

    snapshot = ctx.snapshot
    assert_can_download(snapshot)

    if not documents_info:
        raise HTTPException(status_code=400, detail="no_documents_selected")

    for doc_info in documents_info:
        dataset = doc_info.get("dataset", "展厅")
        assert_kb_allowed(snapshot, dataset)

    zip_content, filename = deps.ragflow_service.batch_download_documents(documents_info)
    if zip_content is None:
        logger.error("[BATCH DOWNLOAD] Failed to create zip - service returned None")
        raise HTTPException(status_code=500, detail="批量下载失败")

    for doc_info in documents_info:
        doc_id = doc_info.get("doc_id") or doc_info.get("id")
        doc_name = doc_info.get("name", "unknown")
        dataset = doc_info.get("dataset", "展厅")
        kb_info = resolve_kb_ref(deps, dataset)

        deps.download_log_store.log_download(
            doc_id=doc_id,
            filename=doc_name,
            kb_id=(kb_info.dataset_id or dataset),
            downloaded_by=ctx.payload.sub,
            ragflow_doc_id=doc_id,
            is_batch=True,
            kb_dataset_id=kb_info.dataset_id,
            kb_name=(kb_info.name or dataset),
        )

    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/downloads")
async def list_downloads(
    ctx: AuthContextDep,
    kb_id: Optional[str] = None,
    downloaded_by: Optional[str] = None,
    limit: int = 100,
):
    deps = ctx.deps
    if kb_id:
        assert_kb_allowed(ctx.snapshot, kb_id)
        kb_refs = list(resolve_kb_ref(deps, kb_id).variants)
    else:
        kb_refs = None

    if not ctx.snapshot.is_admin:
        downloaded_by = ctx.payload.sub

    downloads = deps.download_log_store.list_downloads(kb_refs=kb_refs, downloaded_by=downloaded_by, limit=limit)

    return {
        "downloads": [
            {
                "id": d.id,
                "doc_id": d.doc_id,
                "filename": d.filename,
                "kb_id": (d.kb_name or d.kb_id),
                "downloaded_by": d.downloaded_by,
                "downloaded_at_ms": d.downloaded_at_ms,
                "ragflow_doc_id": d.ragflow_doc_id,
                "is_batch": d.is_batch,
            }
            for d in downloads
        ],
        "count": len(downloads),
    }

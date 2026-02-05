import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import (
    assert_can_delete,
    assert_can_download,
    assert_kb_allowed,
)
from backend.services.documents.document_manager import DocumentManager
from backend.services.documents.models import DocumentRef

router = APIRouter()
logger = logging.getLogger(__name__)


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
    logger.info("[DOWNLOAD] doc_id=%s dataset=%s user=%s", doc_id, dataset, ctx.payload.sub)
    mgr = DocumentManager(ctx.deps)
    return mgr.download_ragflow_response(doc_id=doc_id, dataset=dataset, filename=filename, ctx=ctx)


@router.get("/documents/{doc_id}/preview")
async def preview_document(
    doc_id: str,
    ctx: AuthContextDep,
    dataset: str = "展厅",
):
    logger.info("[PREVIEW] doc_id=%s dataset=%s user=%s", doc_id, dataset, ctx.payload.sub)

    snapshot = ctx.snapshot
    assert_kb_allowed(snapshot, dataset)
    mgr = DocumentManager(ctx.deps)
    return mgr.preview_payload(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset))


@router.delete("/documents/{doc_id}")
async def delete_ragflow_document(
    doc_id: str,
    ctx: AuthContextDep,
    dataset_name: str = "展厅",
):
    logger.info("[DELETE] doc_id=%s dataset=%s user=%s", doc_id, dataset_name, ctx.payload.sub)
    mgr = DocumentManager(ctx.deps)
    mgr.delete_ragflow_document(doc_id=doc_id, dataset_name=dataset_name, ctx=ctx)
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
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
    )

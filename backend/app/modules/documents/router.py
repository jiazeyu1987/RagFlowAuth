from __future__ import annotations

import io
import os
import time
import zipfile

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import Response

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import assert_can_download, assert_kb_allowed
from backend.services.documents.document_manager import DocumentManager

router = APIRouter()


@router.get("/documents/{source}/{doc_id}/download")
async def download_document_unified(
    source: str,
    doc_id: str,
    ctx: AuthContextDep,
    dataset: str = "展厅",
    filename: str | None = None,
):
    """
    Unified download entrypoint.
    - source=ragflow: requires dataset
    - source=knowledge: ignores dataset/filename and returns FileResponse
    """
    src = (source or "").strip().lower()
    mgr = DocumentManager(ctx.deps)
    if src == "ragflow":
        return mgr.download_ragflow_response(doc_id=doc_id, dataset=dataset, filename=filename, ctx=ctx)
    if src == "knowledge":
        return mgr.download_knowledge_response(doc_id=doc_id, ctx=ctx)
    raise HTTPException(status_code=400, detail="invalid_source")


@router.delete("/documents/{source}/{doc_id}")
async def delete_document_unified(
    source: str,
    doc_id: str,
    ctx: AuthContextDep,
    dataset_name: str = "展厅",
):
    """
    Unified delete entrypoint.
    - source=ragflow: requires dataset_name
    - source=knowledge: ignores dataset_name
    """
    src = (source or "").strip().lower()
    mgr = DocumentManager(ctx.deps)
    if src == "ragflow":
        mgr.delete_ragflow_document(doc_id=doc_id, dataset_name=dataset_name, ctx=ctx)
        return {"message": "文档已删除"}
    if src == "knowledge":
        result = mgr.delete_knowledge_document(doc_id=doc_id, ctx=ctx)
        return {"message": result.message or "文档已删除"}
    raise HTTPException(status_code=400, detail="invalid_source")


@router.post("/documents/knowledge/upload", status_code=201)
async def upload_knowledge_unified(
    request: Request,
    ctx: AuthContextDep,
    file: UploadFile = File(...),
):
    """
    Unified upload entrypoint (knowledge local staging).
    Equivalent to `/api/knowledge/upload`.
    """
    kb_ref = request.query_params.get("kb_id", "展厅")
    mgr = DocumentManager(ctx.deps)
    doc = await mgr.stage_upload_knowledge(kb_ref=kb_ref, upload_file=file, ctx=ctx)

    # Keep the same response shape as the existing knowledge upload endpoint.
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


@router.post("/documents/{source}/batch/download")
async def batch_download_documents_unified(
    source: str,
    request: Request,
    ctx: AuthContextDep,
):
    """
    Unified batch download entrypoint.

    - source=knowledge: body { doc_ids: [<doc_id>, ...] }
    - source=ragflow: body { documents: [{doc_id|id, name, dataset}, ...] }
    """
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_download(snapshot)

    src = (source or "").strip().lower()
    data = await request.json()

    if src == "knowledge":
        doc_ids = data.get("doc_ids", [])
        valid_docs = []
        for doc_id in doc_ids:
            doc = deps.kb_store.get_document(doc_id)
            if not doc:
                continue
            assert_kb_allowed(snapshot, doc.kb_id)
            if not os.path.exists(doc.file_path):
                continue
            valid_docs.append(doc)

        if not valid_docs:
            raise HTTPException(status_code=404, detail="娌℃湁鎵惧埌鍙笅杞界殑鏂囨。")

        zip_buffer = io.BytesIO()
        created_at_ms = int(time.time() * 1000)
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            used_names: set[str] = set()
            for doc in valid_docs:
                zip_name = doc.filename
                counter = 1
                base, ext = os.path.splitext(zip_name)
                while zip_name in used_names:
                    zip_name = f"{base}_{counter}{ext}"
                    counter += 1
                used_names.add(zip_name)
                zip_file.write(doc.file_path, zip_name)

        zip_buffer.seek(0)
        zip_filename = f"documents_{created_at_ms}.zip"
        for doc in valid_docs:
            deps.download_log_store.log_download(
                doc_id=doc.doc_id,
                filename=doc.filename,
                kb_id=(doc.kb_name or doc.kb_id),
                downloaded_by=ctx.payload.sub,
                is_batch=True,
                kb_dataset_id=doc.kb_dataset_id,
                kb_name=doc.kb_name,
            )

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
        )

    if src == "ragflow":
        documents_info = data.get("documents", [])
        if not documents_info:
            raise HTTPException(status_code=400, detail="no_documents_selected")

        for doc_info in documents_info:
            dataset = doc_info.get("dataset", "灞曞巺")
            assert_kb_allowed(snapshot, dataset)

        zip_content, filename = deps.ragflow_service.batch_download_documents(documents_info)
        if zip_content is None:
            raise HTTPException(status_code=500, detail="鎵归噺涓嬭浇澶辫触")

        for doc_info in documents_info:
            doc_id = doc_info.get("doc_id") or doc_info.get("id")
            doc_name = doc_info.get("name", "unknown")
            dataset = doc_info.get("dataset", "灞曞巺")
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

    raise HTTPException(status_code=400, detail="invalid_source")

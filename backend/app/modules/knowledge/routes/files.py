from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pathlib import Path
import os
import zipfile
import io

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import (
    assert_can_download,
    assert_can_review,
    assert_kb_allowed,
)
from backend.services.documents.document_manager import DocumentManager


router = APIRouter()


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    ctx: AuthContextDep,
):
    mgr = DocumentManager(ctx.deps)
    return mgr.download_knowledge_response(doc_id=doc_id, ctx=ctx)


@router.get("/documents/{doc_id}/preview")
async def preview_document(
    request: Request,
    doc_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    # allow either review or download capability to preview
    DocumentManager(deps).assert_can_preview_knowledge(snapshot)

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    from urllib.parse import quote

    ext = Path(doc.filename).suffix.lower()
    render = (request.query_params.get("render") or "").strip().lower()
    media_type = doc.mime_type
    if ext in {".txt", ".ini", ".log"}:
        media_type = "text/plain; charset=utf-8"
    elif ext in {".md", ".markdown"}:
        media_type = "text/markdown; charset=utf-8"
    elif ext in {".doc", ".docx", ".xlsx", ".xls"} and render == "html":
        try:
            from backend.app.core.paths import resolve_repo_path
            from backend.services.office_to_html import convert_office_path_to_html_bytes

            previews_dir = resolve_repo_path("data/previews")
            previews_dir.mkdir(parents=True, exist_ok=True)
            cached_html = previews_dir / f"{doc_id}.html"

            try:
                src_mtime = os.path.getmtime(doc.file_path)
            except Exception:
                src_mtime = None

            if cached_html.exists() and src_mtime is not None:
                try:
                    if os.path.getmtime(cached_html) >= src_mtime:
                        quoted = quote(f"{Path(doc.filename).stem}.html")
                        return FileResponse(
                            path=str(cached_html),
                            media_type="text/html; charset=utf-8",
                            headers={"Content-Disposition": f"inline; filename*=UTF-8''{quoted}"},
                        )
                except Exception:
                    pass

            html_bytes = convert_office_path_to_html_bytes(doc.file_path)
            cached_html.write_bytes(html_bytes)

            quoted = quote(f"{Path(doc.filename).stem}.html")
            return FileResponse(
                path=str(cached_html),
                media_type="text/html; charset=utf-8",
                headers={"Content-Disposition": f"inline; filename*=UTF-8''{quoted}"},
            )
        except Exception as e:
            raise HTTPException(status_code=415, detail=f"Office 在线预览不可用：{str(e)}")

    quoted = quote(doc.filename)
    return FileResponse(
        path=doc.file_path,
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quoted}",
        },
    )


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
    import time

    logger = logging.getLogger(__name__)

    deps = ctx.deps
    doc_ids = body.get("doc_ids", [])
    logger.info(f"[BATCH DOWNLOAD] Request to download {len(doc_ids)} documents")
    logger.info(f"[BATCH DOWNLOAD] User: {ctx.payload.sub}")

    snapshot = ctx.snapshot
    assert_can_download(snapshot)

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

        if not os.path.exists(doc.file_path):
            logger.warning(f"[BATCH DOWNLOAD] File not found: {doc.file_path}")
            continue

        valid_docs.append(doc)

    if len(valid_docs) == 0:
        raise HTTPException(status_code=404, detail="没有找到可下载的文档")

    logger.info(f"[BATCH DOWNLOAD] Found {len(valid_docs)} valid documents for download")

    zip_buffer = io.BytesIO()
    created_at_ms = int(time.time() * 1000)

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for doc in valid_docs:
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

    zip_filename = f"documents_{created_at_ms}.zip"

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

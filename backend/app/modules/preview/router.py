from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_can_download, assert_can_review, assert_kb_allowed
from backend.services.unified_preview import build_preview_payload

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/preview/documents/{source}/{doc_id}/preview")
async def preview_gateway(
    source: str,
    doc_id: str,
    ctx: AuthContextDep,
    dataset: str = "展厅",
):
    """
    Unified preview gateway for both "ragflow" and "knowledge" document sources.

    Returns the same JSON contract as `/api/ragflow/documents/{doc_id}/preview`:
      - text/image/pdf/html/unsupported
    """
    deps = ctx.deps
    snapshot = ctx.snapshot

    src = (source or "").strip().lower()
    if src == "ragflow":
        assert_kb_allowed(snapshot, dataset)
        try:
            file_content, filename = deps.ragflow_service.download_document(doc_id, dataset)
        except Exception as e:
            logger.exception("[PreviewGateway] ragflow download exception: %s", e)
            raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")
        if file_content is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        return build_preview_payload(file_content, filename, doc_id=doc_id)

    if src == "knowledge":
        # allow either review or download capability to preview
        try:
            assert_can_download(snapshot)
        except Exception:
            assert_can_review(snapshot)

        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        assert_kb_allowed(snapshot, doc.kb_id)

        file_path = getattr(doc, "file_path", None)
        filename = getattr(doc, "filename", None)
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
        except Exception as e:
            logger.exception("[PreviewGateway] knowledge read exception: %s", e)
            raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")

        return build_preview_payload(file_content, filename, doc_id=doc_id)

    raise HTTPException(status_code=400, detail="invalid_source")

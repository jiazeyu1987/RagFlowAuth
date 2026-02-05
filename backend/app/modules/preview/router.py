from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_kb_allowed
from backend.services.documents.document_manager import DocumentManager
from backend.services.documents.models import DocumentRef

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
        mgr = DocumentManager(deps)
        return mgr.preview_payload(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset))

    if src == "knowledge":
        mgr = DocumentManager(deps)
        # Permission/KB checks happen in the knowledge routes; here just ensure KB allowed
        # by loading the document record.
        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        assert_kb_allowed(snapshot, doc.kb_id)
        return mgr.preview_payload(DocumentRef(source="knowledge", doc_id=doc_id))

    raise HTTPException(status_code=400, detail="invalid_source")

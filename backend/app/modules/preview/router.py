from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_kb_allowed
from backend.services.documents.document_manager import DocumentManager
from backend.services.documents.models import DocumentRef
from backend.services.audit_helpers import actor_fields_from_ctx

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/preview/documents/{source}/{doc_id}/preview")
async def preview_gateway(
    source: str,
    doc_id: str,
    ctx: AuthContextDep,
    dataset: str = "展厅",
    render: str = "default",
):
    """
    Unified preview gateway for both "ragflow" and "knowledge" document sources.

    Returns a unified JSON contract:
      - text/image/pdf/html/excel/unsupported

    Query params:
      - dataset: ragflow dataset name (ragflow only)
      - render: "default" | "html"
        - For Excel: default returns `{type:'excel', sheets:{...}}` (fast, no download permission needed)
        - render=html returns `{type:'html', content: base64_html}` for "original preview"
    """
    deps = ctx.deps
    snapshot = ctx.snapshot

    src = (source or "").strip().lower()
    if src == "ragflow":
        assert_kb_allowed(snapshot, dataset)
        mgr = DocumentManager(deps)
        payload = mgr.preview_payload(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset), render=render)
        audit = getattr(deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_preview",
                    actor=ctx.payload.sub,
                    source="ragflow",
                    doc_id=doc_id,
                    filename=str(payload.get("filename") or ""),
                    kb_id=dataset,
                    kb_name=dataset,
                    meta={"render": render, "type": payload.get("type")},
                    **actor_fields_from_ctx(deps, ctx),
                )
            except Exception:
                pass
        return payload

    if src == "knowledge":
        mgr = DocumentManager(deps)
        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        assert_kb_allowed(snapshot, doc.kb_id)
        payload = mgr.preview_payload(DocumentRef(source="knowledge", doc_id=doc_id), render=render)
        audit = getattr(deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_preview",
                    actor=ctx.payload.sub,
                    source="knowledge",
                    doc_id=doc_id,
                    filename=str(payload.get("filename") or getattr(doc, "filename", "") or ""),
                    kb_id=(getattr(doc, "kb_name", None) or getattr(doc, "kb_id", None) or ""),
                    kb_dataset_id=getattr(doc, "kb_dataset_id", None),
                    kb_name=getattr(doc, "kb_name", None) or getattr(doc, "kb_id", None),
                    meta={"render": render, "type": payload.get("type")},
                    **actor_fields_from_ctx(deps, ctx),
                )
            except Exception:
                pass
        return payload

    raise HTTPException(status_code=400, detail="invalid_source")

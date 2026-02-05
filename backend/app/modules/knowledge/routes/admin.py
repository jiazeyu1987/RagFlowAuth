from fastapi import APIRouter, HTTPException
from typing import Optional
import os

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import (
    ResourceScope,
    assert_can_delete,
    assert_kb_allowed,
)
from backend.services.documents.document_manager import DocumentManager


router = APIRouter()


@router.get("/stats")
async def get_stats(ctx: AuthContextDep):
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
async def delete_document(doc_id: str, ctx: AuthContextDep):
    mgr = DocumentManager(ctx.deps)
    result = mgr.delete_knowledge_document(doc_id=doc_id, ctx=ctx)
    return {"message": result.message or "文档已删除"}


@router.get("/deletions")
async def list_deletions(
    ctx: AuthContextDep,
    kb_id: Optional[str] = None,
    limit: int = 100,
):
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

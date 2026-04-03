from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import (
    ResourceScope,
    assert_kb_allowed,
)


router = APIRouter()


@router.get("/stats")
def get_stats(ctx: AuthContextDep):
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


@router.delete("/documents/{doc_id}", status_code=202)
async def delete_document(doc_id: str, ctx: AuthContextDep):
    service = getattr(ctx.deps, "operation_approval_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="operation_approval_service_unavailable")
    try:
        return await service.create_request(
            operation_type="knowledge_file_delete",
            ctx=ctx,
            doc_id=doc_id,
        )
    except Exception as e:
        detail = getattr(e, "code", None) or str(e) or "operation_approval_create_failed"
        status_code = getattr(e, "status_code", 400)
        raise HTTPException(status_code=status_code, detail=detail) from e


@router.get("/deletions")
def list_deletions(
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
    user_ids = {d.deleted_by for d in deletions if d.deleted_by}
    user_ids.update({d.original_uploader for d in deletions if d.original_uploader})
    user_ids.update({d.original_reviewer for d in deletions if d.original_reviewer})
    try:
        usernames = deps.user_store.get_usernames_by_ids(user_ids)
    except Exception:
        usernames = {}

    return {
        "deletions": [
            {
                "id": d.id,
                "doc_id": d.doc_id,
                "filename": d.filename,
                "kb_id": (d.kb_name or d.kb_id),
                "deleted_by": d.deleted_by,
                "deleted_by_name": usernames.get(d.deleted_by) if d.deleted_by else None,
                "deleted_at_ms": d.deleted_at_ms,
                "original_uploader": d.original_uploader,
                "original_uploader_name": usernames.get(d.original_uploader) if d.original_uploader else None,
                "original_reviewer": d.original_reviewer,
                "original_reviewer_name": usernames.get(d.original_reviewer) if d.original_reviewer else None,
                "ragflow_doc_id": d.ragflow_doc_id,
            }
            for d in deletions
        ],
        "count": len(deletions),
    }

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
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_delete(snapshot)

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    assert_kb_allowed(snapshot, doc.kb_id)

    ragflow_ok = None
    ragflow_err = None
    if doc.ragflow_doc_id:
        dataset_ref = doc.kb_dataset_id or doc.kb_id or (doc.kb_name or "")
        try:
            ragflow_ok = 1 if deps.ragflow_service.delete_document(doc.ragflow_doc_id, dataset_name=dataset_ref) else 0
        except Exception as e:
            ragflow_ok = 0
            ragflow_err = str(e)
        if ragflow_ok == 0 and not ragflow_err:
            ragflow_err = "RAGFlow 删除失败"

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
        action="delete",
        ragflow_deleted=ragflow_ok,
        ragflow_delete_error=ragflow_err,
    )

    if ragflow_ok == 0:
        raise HTTPException(status_code=500, detail=f"无法从 RAGFlow 删除该文件：{ragflow_err}")

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    deps.kb_store.delete_document(doc_id)

    return {"message": "文档已删除"}


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

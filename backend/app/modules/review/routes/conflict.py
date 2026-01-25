from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.filename_normalize import normalize_filename_for_conflict
from backend.app.core.permission_resolver import assert_can_review, assert_kb_allowed


router = APIRouter()


@router.get("/documents/{doc_id}/conflict")
async def get_document_conflict(doc_id: str, ctx: AuthContextDep) -> dict:
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    if doc.status != "pending":
        return {"conflict": False}

    normalized = normalize_filename_for_conflict(doc.filename)
    kb_refs = [r for r in {doc.kb_id, doc.kb_dataset_id, doc.kb_name} if r]

    approved = deps.kb_store.list_documents(status="approved", kb_refs=kb_refs, limit=2000)
    existing = None
    for d in approved:
        if d.doc_id == doc.doc_id:
            continue
        if normalize_filename_for_conflict(d.filename) == normalized:
            existing = d
            break

    if not existing:
        return {"conflict": False}

    usernames = {}
    try:
        usernames = deps.user_store.get_usernames_by_ids({existing.uploaded_by, existing.reviewed_by} - {None, ""})
    except Exception:
        usernames = {}

    return {
        "conflict": True,
        "normalized_name": normalized,
        "existing": {
            "doc_id": existing.doc_id,
            "filename": existing.filename,
            "uploaded_by": existing.uploaded_by,
            "uploaded_by_name": usernames.get(existing.uploaded_by) if existing.uploaded_by else None,
            "uploaded_at_ms": existing.uploaded_at_ms,
            "reviewed_by": existing.reviewed_by,
            "reviewed_by_name": usernames.get(existing.reviewed_by) if existing.reviewed_by else None,
            "reviewed_at_ms": existing.reviewed_at_ms,
            "ragflow_doc_id": existing.ragflow_doc_id,
            "kb_id": existing.kb_name or existing.kb_id,
        },
    }


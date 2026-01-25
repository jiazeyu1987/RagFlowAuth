from fastapi import APIRouter, HTTPException
from typing import Optional

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import (
    ResourceScope,
    assert_kb_allowed,
)
from backend.app.core.permdbg import permdbg


router = APIRouter()


@router.get("/documents")
async def list_documents(
    ctx: AuthContextDep,
    status: Optional[str] = None,
    kb_id: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    limit: int = 100,
):
    """
    列出文档，带可选过滤器
    """
    import logging

    logger = logging.getLogger(__name__)

    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    logger.info(f"[LIST DOCS] User: {user.username}, role: {user.role}, kb_id: {kb_id}, status: {status}")
    try:
        permdbg(
            "knowledge.documents.request",
            user=user.username,
            role=user.role,
            kb_scope=snapshot.kb_scope,
            kb_refs=sorted(list(snapshot.kb_names))[:50],
            request_kb_id=kb_id,
        )
    except Exception:
        pass

    if snapshot.kb_scope == ResourceScope.NONE:
        docs = []
    else:
        if kb_id:
            assert_kb_allowed(snapshot, kb_id)
            kb_info = resolve_kb_ref(deps, kb_id)
            docs = deps.kb_store.list_documents(
                status=status,
                kb_refs=list(kb_info.variants),
                uploaded_by=uploaded_by,
                limit=limit,
            )
        else:
            docs = deps.kb_store.list_documents(status=status, kb_id=None, uploaded_by=uploaded_by, limit=limit)
            before = len(docs)
            if snapshot.kb_scope != ResourceScope.ALL:
                docs = [
                    d
                    for d in docs
                    if (d.kb_id in snapshot.kb_names)
                    or (d.kb_dataset_id is not None and d.kb_dataset_id in snapshot.kb_names)
                    or (d.kb_name is not None and d.kb_name in snapshot.kb_names)
                ]
            try:
                permdbg(
                    "knowledge.documents.filtered",
                    before=before,
                    after=len(docs),
                )
            except Exception:
                pass

    logger.info(f"[LIST DOCS] Found {len(docs)} documents")

    user_ids = {d.uploaded_by for d in docs if d.uploaded_by}
    user_ids.update({d.reviewed_by for d in docs if d.reviewed_by})
    try:
        usernames = deps.user_store.get_usernames_by_ids(user_ids)
    except Exception:
        usernames = {}

    return {
        "documents": [
            {
                "doc_id": d.doc_id,
                "filename": d.filename,
                "file_size": d.file_size,
                "mime_type": d.mime_type,
                "uploaded_by": d.uploaded_by,
                "uploaded_by_name": usernames.get(d.uploaded_by) if d.uploaded_by else None,
                "status": d.status,
                "uploaded_at_ms": d.uploaded_at_ms,
                "reviewed_by": d.reviewed_by,
                "reviewed_by_name": usernames.get(d.reviewed_by) if d.reviewed_by else None,
                "reviewed_at_ms": d.reviewed_at_ms,
                "review_notes": d.review_notes,
                "ragflow_doc_id": d.ragflow_doc_id,
                "kb_id": (d.kb_name or d.kb_id),
            }
            for d in docs
        ],
        "count": len(docs),
    }


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

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


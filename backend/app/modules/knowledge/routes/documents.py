from fastapi import APIRouter, HTTPException
from typing import Optional

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import (
    ResourceScope,
    assert_kb_allowed,
)
from backend.app.core.permdbg import permdbg
from backend.app.core.signature_support import resolve_signature_service, signature_manifestation_payload
from backend.app.core.user_display import resolve_user_display_names


router = APIRouter()


def _document_payload(
    doc,
    usernames: dict[str, str],
    *,
    signature=None,
    signature_verified: bool | None = None,
) -> dict:
    payload = {
        "doc_id": doc.doc_id,
        "filename": doc.filename,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "uploaded_by": doc.uploaded_by,
        "uploaded_by_name": usernames.get(doc.uploaded_by) if doc.uploaded_by else None,
        "status": doc.status,
        "uploaded_at_ms": doc.uploaded_at_ms,
        "reviewed_by": doc.reviewed_by,
        "reviewed_by_name": usernames.get(doc.reviewed_by) if doc.reviewed_by else None,
        "reviewed_at_ms": doc.reviewed_at_ms,
        "review_notes": doc.review_notes,
        "ragflow_doc_id": doc.ragflow_doc_id,
        "kb_id": (doc.kb_name or doc.kb_id),
        "logical_doc_id": getattr(doc, "logical_doc_id", None),
        "version_no": getattr(doc, "version_no", 1),
        "previous_doc_id": getattr(doc, "previous_doc_id", None),
        "superseded_by_doc_id": getattr(doc, "superseded_by_doc_id", None),
        "is_current": getattr(doc, "is_current", True),
        "effective_status": getattr(doc, "effective_status", None),
        "archived_at_ms": getattr(doc, "archived_at_ms", None),
        "retention_until_ms": getattr(doc, "retention_until_ms", None),
        "file_sha256": getattr(doc, "file_sha256", None),
    }
    payload.update(signature_manifestation_payload(signature, verified=signature_verified) or {})
    return payload


@router.get("/documents")
def list_documents(
    ctx: AuthContextDep,
    status: Optional[str] = None,
    kb_id: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    assigned_to_me: bool = False,
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
        usernames = resolve_user_display_names(ctx.deps, user_ids)
    except Exception:
        usernames = {}

    signature_service = resolve_signature_service(deps)
    signature_map = signature_service.latest_by_records(
        record_type="knowledge_document_review",
        record_ids=[d.doc_id for d in docs],
    )
    signature_verified_map = {
        record_id: bool(signature_service.verify_signature(signature_id=signature.signature_id))
        for record_id, signature in signature_map.items()
    }

    return {
        "documents": [
            _document_payload(
                d,
                usernames,
                signature=signature_map.get(d.doc_id),
                signature_verified=signature_verified_map.get(d.doc_id),
            )
            for d in docs
        ],
        "count": len(docs),
    }


@router.get("/documents/{doc_id}")
def get_document(
    doc_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    usernames = {}
    try:
        usernames = resolve_user_display_names(ctx.deps, {doc.uploaded_by, doc.reviewed_by} - {None, ""})
    except Exception:
        usernames = {}

    signature_service = resolve_signature_service(deps)
    signature = signature_service.latest_by_record(
        record_type="knowledge_document_review",
        record_id=doc.doc_id,
    )
    signature_verified = None
    if signature is not None:
        signature_verified = bool(signature_service.verify_signature(signature_id=signature.signature_id))

    return _document_payload(
        doc,
        usernames,
        signature=signature,
        signature_verified=signature_verified,
    )

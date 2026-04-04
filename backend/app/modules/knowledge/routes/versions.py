from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_kb_allowed
from backend.app.core.signature_support import resolve_signature_service, signature_manifestation_payload
from backend.app.core.user_display import resolve_user_display_names


router = APIRouter()


def _version_payload(doc, usernames: dict[str, str], *, signature=None, signature_verified: bool | None = None) -> dict:
    payload = {
        "doc_id": doc.doc_id,
        "filename": doc.filename,
        "uploaded_by": doc.uploaded_by,
        "uploaded_by_name": usernames.get(doc.uploaded_by) if doc.uploaded_by else None,
        "status": doc.status,
        "uploaded_at_ms": doc.uploaded_at_ms,
        "reviewed_by": doc.reviewed_by,
        "reviewed_by_name": usernames.get(doc.reviewed_by) if doc.reviewed_by else None,
        "reviewed_at_ms": doc.reviewed_at_ms,
        "review_notes": doc.review_notes,
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


@router.get("/documents/{doc_id}/versions")
def list_document_versions(doc_id: str, ctx: AuthContextDep, limit: int = 100):
    deps = ctx.deps
    snapshot = ctx.snapshot
    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)
    versions = deps.kb_store.list_versions(doc_id, limit=limit)
    current = deps.kb_store.get_current_document(doc_id)

    user_ids = {getattr(item, "uploaded_by", None) for item in versions if getattr(item, "uploaded_by", None)}
    user_ids.update({getattr(item, "reviewed_by", None) for item in versions if getattr(item, "reviewed_by", None)})
    try:
        usernames = resolve_user_display_names(ctx.deps, user_ids)
    except Exception:
        usernames = {}

    signature_service = resolve_signature_service(deps)
    signature_map = signature_service.latest_by_records(
        record_type="knowledge_document_review",
        record_ids=[item.doc_id for item in versions],
    )
    signature_verified_map = {
        record_id: bool(signature_service.verify_signature(signature_id=signature.signature_id))
        for record_id, signature in signature_map.items()
    }

    return {
        "logical_doc_id": (getattr(current, "logical_doc_id", None) or getattr(doc, "logical_doc_id", None) or doc.doc_id),
        "current_doc_id": getattr(current, "doc_id", None),
        "count": len(versions),
        "versions": [
            _version_payload(
                item,
                usernames,
                signature=signature_map.get(item.doc_id),
                signature_verified=signature_verified_map.get(item.doc_id),
            )
            for item in versions
        ],
    }

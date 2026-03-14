from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.authz import AuthContextDep
from backend.app.core.filename_normalize import normalize_filename_for_conflict
from backend.app.core.permission_resolver import assert_can_review, assert_kb_allowed
from backend.models.document import DocumentResponse
from backend.services.audit_helpers import actor_fields_from_ctx


router = APIRouter()


def _to_document_response(doc) -> DocumentResponse:
    return DocumentResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        uploaded_by=doc.uploaded_by,
        status=doc.status,
        uploaded_at_ms=doc.uploaded_at_ms,
        reviewed_by=doc.reviewed_by,
        reviewed_at_ms=doc.reviewed_at_ms,
        review_notes=doc.review_notes,
        ragflow_doc_id=doc.ragflow_doc_id,
        kb_id=(doc.kb_name or doc.kb_id),
    )


def _doc_min_payload(doc) -> dict[str, Any]:
    return {
        "doc_id": doc.doc_id,
        "filename": doc.filename,
        "status": doc.status,
        "uploaded_by": doc.uploaded_by,
        "uploaded_at_ms": doc.uploaded_at_ms,
        "reviewed_by": doc.reviewed_by,
        "reviewed_at_ms": doc.reviewed_at_ms,
        "kb_id": (doc.kb_name or doc.kb_id),
    }


def _find_existing_conflict(*, deps, doc):
    normalized = normalize_filename_for_conflict(doc.filename)
    kb_refs = [item for item in {doc.kb_id, doc.kb_dataset_id, doc.kb_name} if item]
    approved = deps.kb_store.list_documents(status="approved", kb_refs=kb_refs, limit=2000)
    for existing in approved:
        if existing.doc_id == doc.doc_id:
            continue
        if normalize_filename_for_conflict(existing.filename) == normalized:
            return normalized, existing
    return normalized, None


def _audit_conflict_resolution(
    *,
    deps,
    ctx: AuthContextDep,
    doc,
    resolution: str,
    reason: str,
    meta: dict[str, Any] | None = None,
) -> None:
    audit = getattr(deps, "audit_log_store", None)
    if audit is None:
        return
    payload_meta: dict[str, Any] = {
        "resolution": str(resolution or "").strip(),
        "reason": str(reason or "").strip(),
    }
    if meta:
        payload_meta.update(meta)
    try:
        audit.log_event(
            action="document_conflict_resolved",
            actor=ctx.payload.sub,
            source="knowledge",
            doc_id=doc.doc_id,
            filename=doc.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            kb_dataset_id=getattr(doc, "kb_dataset_id", None),
            kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
            meta=payload_meta,
            **actor_fields_from_ctx(deps, ctx),
        )
    except Exception:
        pass


@router.get("/documents/conflicts")
async def list_document_conflicts(
    ctx: AuthContextDep,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_review(snapshot)
    pending_docs = deps.kb_store.list_documents(status="pending", limit=max(1, min(int(limit), 200)))
    items: list[dict[str, Any]] = []
    for doc in pending_docs:
        try:
            assert_kb_allowed(snapshot, doc.kb_id)
        except HTTPException:
            continue
        normalized_name, existing = _find_existing_conflict(deps=deps, doc=doc)
        if existing is None:
            continue
        items.append(
            {
                "pending": _doc_min_payload(doc),
                "existing": _doc_min_payload(existing),
                "normalized_name": normalized_name,
            }
        )
    return {
        "total": len(items),
        "items": items,
    }


@router.post("/documents/{doc_id}/resolve-conflict-rename", response_model=DocumentResponse)
async def resolve_conflict_rename(doc_id: str, ctx: AuthContextDep, body: dict | None = None):
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    target_filename = str((body or {}).get("target_filename") or "").strip()
    rename_reason = str((body or {}).get("rename_reason") or "").strip()
    if not target_filename:
        raise HTTPException(status_code=400, detail="target_filename_required")
    if not rename_reason:
        raise HTTPException(status_code=400, detail="rename_reason_required")

    doc = deps.kb_store.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document_not_found")
    assert_kb_allowed(snapshot, doc.kb_id)
    if str(doc.status or "").strip().lower() != "pending":
        raise HTTPException(status_code=400, detail="document_not_pending")

    normalized_target_name = normalize_filename_for_conflict(target_filename)
    kb_refs = [item for item in {doc.kb_id, doc.kb_dataset_id, doc.kb_name} if item]
    approved = deps.kb_store.list_documents(status="approved", kb_refs=kb_refs, limit=2000)
    for existing in approved:
        if existing.doc_id == doc.doc_id:
            continue
        if normalize_filename_for_conflict(existing.filename) == normalized_target_name:
            raise HTTPException(status_code=409, detail="target_filename_conflicts_with_approved_document")

    current_path = Path(str(doc.file_path or ""))
    if not current_path.exists():
        raise HTTPException(status_code=404, detail="local_file_not_found")
    target_path = current_path.with_name(target_filename)
    if target_path != current_path and target_path.exists():
        raise HTTPException(status_code=409, detail="target_file_path_exists")

    try:
        if target_path != current_path:
            current_path.rename(target_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"rename_file_failed:{exc}") from exc

    updated = deps.kb_store.update_document_file_info(
        doc_id=doc.doc_id,
        filename=target_filename,
        file_path=str(target_path),
    )
    if updated is None:
        raise HTTPException(status_code=500, detail="rename_update_failed")

    _audit_conflict_resolution(
        deps=deps,
        ctx=ctx,
        doc=updated,
        resolution="rename",
        reason=rename_reason,
        meta={
            "old_filename": doc.filename,
            "new_filename": updated.filename,
        },
    )
    return _to_document_response(updated)


@router.post("/documents/{doc_id}/resolve-conflict-skip", response_model=DocumentResponse)
async def resolve_conflict_skip(doc_id: str, ctx: AuthContextDep, body: dict | None = None):
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    skip_reason = str((body or {}).get("skip_reason") or "").strip()
    if not skip_reason:
        raise HTTPException(status_code=400, detail="skip_reason_required")

    doc = deps.kb_store.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document_not_found")
    assert_kb_allowed(snapshot, doc.kb_id)
    if str(doc.status or "").strip().lower() != "pending":
        raise HTTPException(status_code=400, detail="document_not_pending")

    updated = deps.kb_store.update_document_status(
        doc_id=doc.doc_id,
        status="rejected",
        reviewed_by=ctx.payload.sub,
        review_notes=f"[conflict_skip] {skip_reason}",
    )
    if updated is None:
        raise HTTPException(status_code=500, detail="skip_update_failed")

    _audit_conflict_resolution(
        deps=deps,
        ctx=ctx,
        doc=updated,
        resolution="skip",
        reason=skip_reason,
        meta={
            "old_status": doc.status,
            "new_status": updated.status,
        },
    )
    return _to_document_response(updated)

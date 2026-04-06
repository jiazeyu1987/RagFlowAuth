from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.models.knowledge import KnowledgeDeletionListEnvelope
from backend.models.operation_approval import OperationApprovalRequestBrief, OperationApprovalRequestEnvelope
from backend.app.core.permission_resolver import (
    assert_kb_allowed,
)
from backend.app.core.user_display import resolve_user_display_names


router = APIRouter()


def _wrap_operation_request(brief: dict) -> dict[str, dict]:
    return {"request": OperationApprovalRequestBrief(**brief).model_dump()}


def _resolve_usernames(deps, user_ids: set[str]) -> dict[str, str]:
    try:
        resolved = resolve_user_display_names(deps, user_ids)
    except Exception as exc:
        raise HTTPException(
            status_code=int(getattr(exc, "status_code", 500) or 500),
            detail=str(exc).strip() or "knowledge_deletions_user_lookup_failed",
        ) from exc
    if not isinstance(resolved, dict):
        raise HTTPException(status_code=502, detail="knowledge_deletions_invalid_payload")
    return resolved


def _serialize_deletions(deletions: object, usernames: dict[str, str]) -> list[dict]:
    if not isinstance(deletions, list):
        raise HTTPException(status_code=502, detail="knowledge_deletions_invalid_payload")
    items: list[dict] = []
    for deletion in deletions:
        try:
            items.append(
                {
                    "id": deletion.id,
                    "doc_id": deletion.doc_id,
                    "filename": deletion.filename,
                    "kb_id": (deletion.kb_name or deletion.kb_id),
                    "deleted_by": deletion.deleted_by,
                    "deleted_by_name": usernames.get(deletion.deleted_by) if deletion.deleted_by else None,
                    "deleted_at_ms": deletion.deleted_at_ms,
                    "original_uploader": deletion.original_uploader,
                    "original_uploader_name": usernames.get(deletion.original_uploader) if deletion.original_uploader else None,
                    "original_reviewer": deletion.original_reviewer,
                    "original_reviewer_name": usernames.get(deletion.original_reviewer) if deletion.original_reviewer else None,
                    "ragflow_doc_id": deletion.ragflow_doc_id,
                }
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail="knowledge_deletions_invalid_payload") from exc
    return items


@router.delete("/documents/{doc_id}", response_model=OperationApprovalRequestEnvelope, status_code=202)
async def delete_document(doc_id: str, ctx: AuthContextDep):
    service = getattr(ctx.deps, "operation_approval_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="operation_approval_service_unavailable")
    try:
        brief = await service.create_request(
            operation_type="knowledge_file_delete",
            ctx=ctx,
            doc_id=doc_id,
        )
    except Exception as e:
        detail = getattr(e, "code", None) or str(e) or "operation_approval_create_failed"
        status_code = getattr(e, "status_code", 400)
        raise HTTPException(status_code=status_code, detail=detail) from e
    return _wrap_operation_request(brief)


@router.get("/deletions", response_model=KnowledgeDeletionListEnvelope)
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
    if not isinstance(deletions, list):
        raise HTTPException(status_code=502, detail="knowledge_deletions_invalid_payload")
    user_ids = {d.deleted_by for d in deletions if d.deleted_by}
    user_ids.update({d.original_uploader for d in deletions if d.original_uploader})
    user_ids.update({d.original_reviewer for d in deletions if d.original_reviewer})
    usernames = _resolve_usernames(deps, user_ids)
    items = _serialize_deletions(deletions, usernames)

    return {
        "deletions": items,
        "count": len(items),
    }

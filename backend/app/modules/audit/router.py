from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.authz import AdminOnly, AuthContextDep

router = APIRouter()


@router.get("/audit/events")
async def list_audit_events(
    ctx: AuthContextDep,
    _: AdminOnly,
    action: str | None = None,
    actor: str | None = None,
    username: str | None = None,
    company_id: int | None = None,
    department_id: int | None = None,
    source: str | None = None,
    kb_ref: str | None = None,
    from_ms: int | None = None,
    to_ms: int | None = None,
    offset: int = 0,
    limit: int = 200,
):
    """
    Unified audit events list (admin only).

    Covers:
    - auth_login/auth_logout
    - document_preview/document_upload/document_download/document_delete
    """
    store = ctx.deps.audit_log_store
    total, rows = store.list_events(
        action=action,
        actor=actor,
        actor_username=username,
        company_id=company_id,
        department_id=department_id,
        source=source,
        kb_ref=kb_ref,
        from_ms=from_ms,
        to_ms=to_ms,
        offset=offset,
        limit=limit,
    )
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "action": r.action,
                "actor": r.actor,
                "username": r.actor_username,
                "company_id": r.company_id,
                "company_name": r.company_name,
                "department_id": r.department_id,
                "department_name": r.department_name,
                "created_at_ms": r.created_at_ms,
                "source": r.source,
                "doc_id": r.doc_id,
                "filename": r.filename,
                "kb_id": r.kb_id,
                "kb_dataset_id": r.kb_dataset_id,
                "kb_name": r.kb_name,
                "meta_json": r.meta_json,
            }
            for r in rows
        ],
    }

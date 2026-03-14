from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.services.feature_visibility import assert_feature_visible_or_404
from backend.services.feature_visibility_store import FLAG_API_AUDIT_EVENTS_VISIBLE

router = APIRouter()


@router.get("/audit/events")
async def list_audit_events(
    ctx: AuthContextDep,
    _: AdminOnly,
    action: str | None = None,
    actor: str | None = None,
    role: str | None = None,
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
    assert_feature_visible_or_404(
        deps=ctx.deps,
        user=ctx.user,
        flag_key=FLAG_API_AUDIT_EVENTS_VISIBLE,
    )

    """
    Unified audit events list (admin only).

    Covers:
    - auth_login/auth_logout
    - document_preview/document_upload/document_download/document_delete
    """
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        manager = ctx.deps.audit_log_store
    if hasattr(manager, "list_events") and manager is not ctx.deps.audit_log_store:
        return manager.list_events(
            action=action,
            actor=actor,
            actor_role=role,
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
    total, rows = ctx.deps.audit_log_store.list_events(
        action=action,
        actor=actor,
        actor_role=role,
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

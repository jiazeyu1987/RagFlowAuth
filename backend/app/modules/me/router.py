from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import ResourceScope
from backend.services.audit_helpers import actor_fields_from_ctx
from backend.services.notification import NotificationManager, NotificationManagerError

router = APIRouter()


class MessageReadStateBody(BaseModel):
    read: bool


def _resolve_notification_manager(ctx: AuthContextDep) -> NotificationManager:
    manager = getattr(ctx.deps, "notification_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="notification_manager_unavailable")
    return manager


def _notification_audit_payload(ctx: AuthContextDep, request: Request) -> dict[str, Any]:
    return {
        "actor": str(ctx.payload.sub),
        "source": "notification",
        "request_id": getattr(getattr(request, "state", None), "request_id", None),
        "client_ip": getattr(getattr(request, "client", None), "host", None),
        "actor_fields": actor_fields_from_ctx(ctx.deps, ctx),
    }


@router.get("/me/kbs")
def get_my_kbs(ctx: AuthContextDep):
    """
    Compatibility endpoint for older frontend calls.

    Returns:
      {
        "kb_ids": [...],   # preferred: dataset ids
        "kb_names": [...], # for display only
      }
    """
    deps = ctx.deps
    snapshot = ctx.snapshot

    if snapshot.kb_scope == ResourceScope.ALL:
        datasets = (
            deps.ragflow_service.list_all_datasets()
            if hasattr(deps.ragflow_service, "list_all_datasets")
            else deps.ragflow_service.list_datasets()
        )
        kb_ids = [ds.get("id") for ds in (datasets or []) if isinstance(ds, dict) and ds.get("id")]
        kb_names = [ds.get("name") for ds in (datasets or []) if isinstance(ds, dict) and ds.get("name")]
        return {"kb_ids": sorted(set(kb_ids)), "kb_names": sorted(set(kb_names))}

    if snapshot.kb_scope == ResourceScope.NONE:
        return {"kb_ids": [], "kb_names": []}

    refs = set(snapshot.kb_names)
    kb_ids = (
        list(deps.ragflow_service.normalize_dataset_ids(refs))
        if hasattr(deps.ragflow_service, "normalize_dataset_ids")
        else []
    )
    if not kb_ids:
        kb_ids = sorted(refs)

    kb_names = (
        list(deps.ragflow_service.resolve_dataset_names(refs))
        if hasattr(deps.ragflow_service, "resolve_dataset_names")
        else sorted(refs)
    )

    return {"kb_ids": sorted(set([x for x in kb_ids if isinstance(x, str) and x])), "kb_names": sorted(set([x for x in kb_names if isinstance(x, str) and x]))}


@router.get("/me/messages")
def list_my_messages(
    ctx: AuthContextDep,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
):
    manager = _resolve_notification_manager(ctx)
    try:
        data = manager.list_inbox(
            recipient_user_id=str(ctx.payload.sub),
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        )
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e
    items = data.get("items") or []
    return {
        "items": items,
        "count": len(items),
        "total": int(data.get("total") or 0),
        "unread_count": int(data.get("unread_count") or 0),
    }


@router.patch("/me/messages/{job_id}/read-state")
def update_message_read_state(
    job_id: int,
    body: MessageReadStateBody,
    request: Request,
    ctx: AuthContextDep,
):
    manager = _resolve_notification_manager(ctx)
    try:
        return manager.update_inbox_read_state(
            job_id=job_id,
            recipient_user_id=str(ctx.payload.sub),
            read=bool(body.read),
            audit=_notification_audit_payload(ctx, request),
        )
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e


@router.post("/me/messages/mark-all-read")
def mark_all_messages_read(
    request: Request,
    ctx: AuthContextDep,
):
    manager = _resolve_notification_manager(ctx)
    try:
        return manager.mark_all_inbox_read(
            recipient_user_id=str(ctx.payload.sub),
            audit=_notification_audit_payload(ctx, request),
        )
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.authz import AuthContextDep
from backend.models.inbox import InboxMarkAllReadResponse, InboxMarkReadResponse
from backend.services.notification import NotificationManager, NotificationManagerError


router = APIRouter()

HIDDEN_OPERATION_APPROVAL_EVENT_TYPES = {
    "operation_approval_submitted",
    "operation_approval_withdrawn",
    "operation_approval_rejected",
    "operation_approval_executed",
    "operation_approval_execution_failed",
}


def _resolve_notification_manager(ctx: AuthContextDep) -> NotificationManager:
    manager = getattr(ctx.deps, "notification_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="notification_manager_unavailable")
    return manager


def _to_legacy_inbox_item(item: dict) -> dict:
    payload = item.get("payload") or {}
    approval_target = payload.get("approval_target") or {}
    return {
        "inbox_id": str(item["job_id"]),
        "title": str(payload.get("title") or payload.get("subject") or item.get("event_type") or "").strip(),
        "body": str(payload.get("body") or "").strip(),
        "status": ("read" if item.get("read_at_ms") else "unread"),
        "event_type": str(item.get("event_type") or ""),
        "link_path": str(payload.get("link_path") or approval_target.get("route_path") or "").strip() or None,
        "payload": payload,
        "created_at_ms": int(item.get("created_at_ms") or 0),
    }


@router.get("/inbox")
def list_inbox(ctx: AuthContextDep, unread_only: bool = False, limit: int = Query(default=100, ge=1, le=500)):
    manager = _resolve_notification_manager(ctx)
    try:
        data = manager.list_inbox(
            recipient_user_id=str(ctx.user.user_id),
            unread_only=bool(unread_only),
            limit=limit,
            offset=0,
        )
    except NotificationManagerError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    items = [
        _to_legacy_inbox_item(item)
        for item in (data.get("items") or [])
        if str(item.get("event_type") or "") not in HIDDEN_OPERATION_APPROVAL_EVENT_TYPES
    ]
    unread_count = sum(1 for item in items if item.get("status") == "unread")
    return {
        "items": items,
        "count": len(items),
        "unread_count": unread_count,
    }


@router.post("/inbox/read-all", response_model=InboxMarkAllReadResponse)
def mark_inbox_read_all(ctx: AuthContextDep):
    manager = _resolve_notification_manager(ctx)
    try:
        result = manager.mark_all_inbox_read(recipient_user_id=str(ctx.user.user_id))
        unread_snapshot = manager.list_inbox(
            recipient_user_id=str(ctx.user.user_id),
            unread_only=True,
            limit=1,
            offset=0,
        )
    except NotificationManagerError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    return InboxMarkAllReadResponse(
        updated=int(result.get("updated_count") or 0),
        unread_count=int(unread_snapshot.get("unread_count") or 0),
    )


@router.post("/inbox/{inbox_id}/read", response_model=InboxMarkReadResponse)
def mark_inbox_read(inbox_id: str, ctx: AuthContextDep):
    manager = _resolve_notification_manager(ctx)
    try:
        updated = manager.update_inbox_read_state(
            job_id=int(inbox_id),
            recipient_user_id=str(ctx.user.user_id),
            read=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="inbox_notification_not_found") from exc
    except NotificationManagerError as exc:
        detail = "inbox_notification_not_found" if exc.code == "notification_message_not_found" else exc.code
        status_code = 404 if detail == "inbox_notification_not_found" else exc.status_code
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return InboxMarkReadResponse(inbox_id=str(updated["job_id"]), status="read")

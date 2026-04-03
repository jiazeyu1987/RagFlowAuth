from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.authz import AuthContextDep
from backend.models.inbox import InboxMarkAllReadResponse, InboxMarkReadResponse
from backend.services.inbox_service import UserInboxError


router = APIRouter()


def _service(ctx: AuthContextDep):
    service = getattr(ctx.deps, "user_inbox_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="user_inbox_service_unavailable")
    return service


@router.get("/inbox")
def list_inbox(ctx: AuthContextDep, unread_only: bool = False, limit: int = Query(default=100, ge=1, le=500)):
    return _service(ctx).list_items(
        recipient_user_id=str(ctx.user.user_id),
        unread_only=bool(unread_only),
        limit=limit,
    )


@router.post("/inbox/read-all", response_model=InboxMarkAllReadResponse)
def mark_inbox_read_all(ctx: AuthContextDep):
    return _service(ctx).mark_all_read(recipient_user_id=str(ctx.user.user_id))


@router.post("/inbox/{inbox_id}/read", response_model=InboxMarkReadResponse)
def mark_inbox_read(inbox_id: str, ctx: AuthContextDep):
    try:
        item = _service(ctx).mark_read(inbox_id=inbox_id, recipient_user_id=str(ctx.user.user_id))
    except UserInboxError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    return InboxMarkReadResponse(inbox_id=str(item["inbox_id"]), status=str(item["status"]))

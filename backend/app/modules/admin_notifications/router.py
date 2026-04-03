from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.services.audit_helpers import actor_fields_from_ctx
from backend.services.notification import NotificationManager, NotificationManagerError

router = APIRouter()


class ChannelUpsertBody(BaseModel):
    channel_type: str
    name: str
    enabled: bool = True
    config: dict[str, Any] | None = None


def _resolve_notification_manager(ctx: AuthContextDep) -> NotificationManager:
    deps = ctx.deps
    manager = getattr(deps, "notification_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="notification_manager_unavailable")
    return manager


def _audit_payload(ctx: AuthContextDep, request: Request) -> dict[str, Any]:
    return {
        "actor": str(ctx.payload.sub),
        "source": "notification",
        "request_id": getattr(getattr(request, "state", None), "request_id", None),
        "client_ip": getattr(getattr(request, "client", None), "host", None),
        "actor_fields": actor_fields_from_ctx(ctx.deps, ctx),
    }


@router.get("/admin/notifications/channels")
def list_channels(ctx: AuthContextDep, _: AdminOnly, enabled_only: bool = False):
    manager = _resolve_notification_manager(ctx)
    items = manager.list_channels(enabled_only=enabled_only)
    return {"items": items, "count": len(items)}


@router.put("/admin/notifications/channels/{channel_id}")
def upsert_channel(channel_id: str, body: ChannelUpsertBody, request: Request, ctx: AuthContextDep, _: AdminOnly):
    manager = _resolve_notification_manager(ctx)
    try:
        item = manager.upsert_channel(
            channel_id=channel_id,
            channel_type=body.channel_type,
            name=body.name,
            enabled=bool(body.enabled),
            config=body.config or {},
            audit=_audit_payload(ctx, request),
        )
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e
    return item


@router.get("/admin/notifications/jobs")
def list_jobs(ctx: AuthContextDep, _: AdminOnly, limit: int = 100, status: str | None = None):
    manager = _resolve_notification_manager(ctx)
    items = manager.list_jobs(limit=limit, status=status)
    return {"items": items, "count": len(items)}


@router.get("/admin/notifications/jobs/{job_id}/logs")
def list_job_logs(ctx: AuthContextDep, _: AdminOnly, job_id: int, limit: int = 50):
    manager = _resolve_notification_manager(ctx)
    items = manager.list_delivery_logs(job_id=job_id, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/admin/notifications/jobs/{job_id}/retry")
def retry_job(ctx: AuthContextDep, request: Request, _: AdminOnly, job_id: int):
    manager = _resolve_notification_manager(ctx)
    try:
        return manager.retry_job(job_id=job_id, audit=_audit_payload(ctx, request))
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e


@router.post("/admin/notifications/jobs/{job_id}/resend")
def resend_job(ctx: AuthContextDep, request: Request, _: AdminOnly, job_id: int):
    manager = _resolve_notification_manager(ctx)
    try:
        return manager.resend_job(job_id=job_id, audit=_audit_payload(ctx, request))
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e


@router.post("/admin/notifications/dispatch")
def dispatch_pending(ctx: AuthContextDep, request: Request, _: AdminOnly, limit: int = 100):
    manager = _resolve_notification_manager(ctx)
    return manager.dispatch_pending(limit=limit, audit=_audit_payload(ctx, request))

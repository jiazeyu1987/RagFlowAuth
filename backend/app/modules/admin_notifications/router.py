from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.core.auth import get_global_deps
from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.core.user_display import resolve_user_display_names
from backend.app.dependencies import AppDependencies
from backend.services.audit_helpers import actor_fields_from_ctx
from backend.services.notification import NotificationManager, NotificationManagerError

router = APIRouter()


class ChannelUpsertBody(BaseModel):
    channel_type: str
    name: str
    enabled: bool = True
    config: dict[str, Any] | None = None


class NotificationRuleBody(BaseModel):
    event_type: str
    enabled_channel_types: list[str] = Field(default_factory=list)


class NotificationRuleBatchBody(BaseModel):
    items: list[NotificationRuleBody] = Field(default_factory=list)


class RecipientMapRebuildInvalidOrgUser(BaseModel):
    employee_user_id: str
    full_name: str
    reason: str


class RecipientMapRebuildResponse(BaseModel):
    channel_id: str
    org_user_count: int
    directory_entry_count: int
    alias_entry_count: int
    invalid_org_user_count: int
    invalid_org_users: list[RecipientMapRebuildInvalidOrgUser] = Field(default_factory=list)


def _resolve_notification_manager(deps: AppDependencies) -> NotificationManager:
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


def _wrap_payload(field: str, item: object) -> dict[str, object]:
    if not isinstance(item, dict):
        raise HTTPException(status_code=500, detail=f"{field}_invalid_payload")
    return {field: item}


@router.get("/admin/notifications/channels")
def list_channels(
    ctx: AuthContextDep,
    _: AdminOnly,
    enabled_only: bool = False,
    global_deps: AppDependencies = Depends(get_global_deps),
):
    manager = _resolve_notification_manager(global_deps)
    items = manager.list_channels(enabled_only=enabled_only)
    return {"items": items, "count": len(items)}


@router.put("/admin/notifications/channels/{channel_id}")
def upsert_channel(
    channel_id: str,
    body: ChannelUpsertBody,
    request: Request,
    ctx: AuthContextDep,
    _: AdminOnly,
    global_deps: AppDependencies = Depends(get_global_deps),
):
    manager = _resolve_notification_manager(global_deps)
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
    return _wrap_payload("channel", item)


@router.post(
    "/admin/notifications/channels/{channel_id}/recipient-map/rebuild-from-org",
    response_model=RecipientMapRebuildResponse,
)
def rebuild_dingtalk_recipient_map(
    channel_id: str,
    request: Request,
    ctx: AuthContextDep,
    _: AdminOnly,
    global_deps: AppDependencies = Depends(get_global_deps),
):
    manager = _resolve_notification_manager(global_deps)
    try:
        return manager.rebuild_dingtalk_recipient_map_from_org(
            channel_id=channel_id,
            user_store=global_deps.user_store,
            org_directory_store=global_deps.org_structure_manager,
            audit=_audit_payload(ctx, request),
        )
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e


@router.get("/admin/notifications/jobs")
def list_jobs(
    ctx: AuthContextDep,
    _: AdminOnly,
    global_deps: AppDependencies = Depends(get_global_deps),
    limit: int = 100,
    status: str | None = None,
    event_type: str | None = None,
    channel_type: str | None = None,
):
    manager = _resolve_notification_manager(global_deps)
    items = manager.list_jobs(limit=limit, status=status, event_type=event_type, channel_type=channel_type)
    names = resolve_user_display_names(
        global_deps,
        {str(item.get("recipient_user_id") or "").strip() for item in items if item.get("recipient_user_id")},
    )
    for item in items:
        user_id = str(item.get("recipient_user_id") or "").strip()
        if user_id and names.get(user_id):
            item["recipient_full_name"] = names.get(user_id)
    return {"items": items, "count": len(items)}


@router.get("/admin/notifications/rules")
def list_rules(ctx: AuthContextDep, _: AdminOnly, global_deps: AppDependencies = Depends(get_global_deps)):
    manager = _resolve_notification_manager(global_deps)
    try:
        return manager.list_event_rules()
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e


@router.put("/admin/notifications/rules")
def upsert_rules(
    body: NotificationRuleBatchBody,
    request: Request,
    ctx: AuthContextDep,
    _: AdminOnly,
    global_deps: AppDependencies = Depends(get_global_deps),
):
    manager = _resolve_notification_manager(global_deps)
    try:
        return manager.upsert_event_rules(
            items=[
                {
                    "event_type": item.event_type,
                    "enabled_channel_types": list(item.enabled_channel_types or []),
                }
                for item in (body.items or [])
            ],
            audit=_audit_payload(ctx, request),
        )
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e


@router.get("/admin/notifications/jobs/{job_id}/logs")
def list_job_logs(
    ctx: AuthContextDep,
    _: AdminOnly,
    job_id: int,
    limit: int = 50,
    global_deps: AppDependencies = Depends(get_global_deps),
):
    manager = _resolve_notification_manager(global_deps)
    items = manager.list_delivery_logs(job_id=job_id, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/admin/notifications/jobs/{job_id}/retry")
def retry_job(
    ctx: AuthContextDep,
    request: Request,
    _: AdminOnly,
    job_id: int,
    global_deps: AppDependencies = Depends(get_global_deps),
):
    manager = _resolve_notification_manager(global_deps)
    try:
        item = manager.retry_job(job_id=job_id, audit=_audit_payload(ctx, request))
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e
    return _wrap_payload("job", item)


@router.post("/admin/notifications/jobs/{job_id}/resend")
def resend_job(
    ctx: AuthContextDep,
    request: Request,
    _: AdminOnly,
    job_id: int,
    global_deps: AppDependencies = Depends(get_global_deps),
):
    manager = _resolve_notification_manager(global_deps)
    try:
        item = manager.resend_job(job_id=job_id, audit=_audit_payload(ctx, request))
    except NotificationManagerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e
    return _wrap_payload("job", item)


@router.post("/admin/notifications/dispatch")
def dispatch_pending(
    ctx: AuthContextDep,
    request: Request,
    _: AdminOnly,
    limit: int = 100,
    global_deps: AppDependencies = Depends(get_global_deps),
):
    manager = _resolve_notification_manager(global_deps)
    item = manager.dispatch_pending(limit=limit, audit=_audit_payload(ctx, request))
    return _wrap_payload("dispatch", item)

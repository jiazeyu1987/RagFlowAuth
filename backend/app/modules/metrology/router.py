from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep, assert_capability
from backend.services.metrology import MetrologyServiceError

router = APIRouter()


class MetrologyRecordBody(BaseModel):
    equipment_id: str
    responsible_user_id: str
    planned_due_date: str
    summary: str
    result_status: str | None = None
    performed_at_ms: int | None = None
    next_due_date: str | None = None
    attachments: list[dict] | None = None
    record_notes: str | None = None


class MetrologyRecordResultBody(BaseModel):
    performed_at_ms: int
    result_status: str
    summary: str
    next_due_date: str | None = None
    attachments: list[dict] | None = None
    record_notes: str | None = None


class MetrologyDecisionBody(BaseModel):
    notes: str | None = None


def _service_from_ctx(ctx: AuthContextDep):
    service = getattr(ctx.deps, "metrology_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="metrology_service_unavailable")
    return service


def _ensure_user_exists(ctx: AuthContextDep, user_id: str, *, field_name: str) -> None:
    user = ctx.deps.user_store.get_by_user_id(str(user_id).strip())
    if user is None:
        raise HTTPException(status_code=400, detail=f"{field_name}_not_found")


def _audit(ctx: AuthContextDep, *, action: str, event_type: str, resource_id: str, before, after, meta=None) -> None:
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        return
    manager.safe_log_ctx_event(
        ctx=ctx,
        action=action,
        source="metrology",
        resource_type="metrology_record",
        resource_id=resource_id,
        event_type=event_type,
        before=before,
        after=after,
        meta=meta or {},
    )


@router.post("/metrology/records")
def create_metrology_record(body: MetrologyRecordBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="metrology", action="record")
    _ensure_user_exists(ctx, body.responsible_user_id, field_name="responsible_user_id")
    service = _service_from_ctx(ctx)
    try:
        item = service.create_record(
            equipment_id=body.equipment_id,
            responsible_user_id=body.responsible_user_id,
            actor_user_id=str(ctx.user.user_id),
            planned_due_date=body.planned_due_date,
            summary=body.summary,
            result_status=body.result_status,
            performed_at_ms=body.performed_at_ms,
            next_due_date=body.next_due_date,
            attachments=body.attachments,
            record_notes=body.record_notes,
        )
    except MetrologyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="metrology_record_create",
        event_type="create",
        resource_id=item["record_id"],
        before=None,
        after=item,
        meta={"status": item["status"], "equipment_id": item["equipment_id"]},
    )
    return item


@router.get("/metrology/records")
def list_metrology_records(
    ctx: AuthContextDep,
    limit: int = 100,
    equipment_id: str | None = None,
    status: str | None = None,
):
    assert_capability(ctx, resource="metrology", action="record")
    service = _service_from_ctx(ctx)
    try:
        items = service.list_records(limit=limit, equipment_id=equipment_id, status=status)
    except MetrologyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    return {"items": items, "count": len(items)}


@router.post("/metrology/records/{record_id}/record")
def record_metrology_result(record_id: str, body: MetrologyRecordResultBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="metrology", action="record")
    service = _service_from_ctx(ctx)
    before = service.get_record(record_id)
    try:
        item = service.record_result(
            record_id=record_id,
            actor_user_id=str(ctx.user.user_id),
            performed_at_ms=body.performed_at_ms,
            result_status=body.result_status,
            summary=body.summary,
            next_due_date=body.next_due_date,
            attachments=body.attachments,
            record_notes=body.record_notes,
        )
    except MetrologyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="metrology_record_record",
        event_type="update",
        resource_id=item["record_id"],
        before=before,
        after=item,
        meta={"status": item["status"], "result_status": item["result_status"]},
    )
    return item


@router.post("/metrology/records/{record_id}/confirm")
def confirm_metrology_record(record_id: str, body: MetrologyDecisionBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="metrology", action="confirm")
    service = _service_from_ctx(ctx)
    before = service.get_record(record_id)
    try:
        item = service.confirm_record(
            record_id=record_id,
            actor_user_id=str(ctx.user.user_id),
            confirmation_notes=body.notes,
        )
    except MetrologyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="metrology_record_confirm",
        event_type="update",
        resource_id=item["record_id"],
        before=before,
        after=item,
        meta={"status": item["status"]},
    )
    return item


@router.post("/metrology/records/{record_id}/approve")
def approve_metrology_record(record_id: str, body: MetrologyDecisionBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="metrology", action="approve")
    service = _service_from_ctx(ctx)
    before = service.get_record(record_id)
    try:
        item = service.approve_record(
            record_id=record_id,
            actor_user_id=str(ctx.user.user_id),
            approval_notes=body.notes,
        )
    except MetrologyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="metrology_record_approve",
        event_type="update",
        resource_id=item["record_id"],
        before=before,
        after=item,
        meta={"status": item["status"]},
    )
    return item


@router.post("/metrology/reminders/dispatch")
def dispatch_metrology_reminders(ctx: AuthContextDep, window_days: int = 7):
    assert_capability(ctx, resource="metrology", action="record")
    service = _service_from_ctx(ctx)
    try:
        result = service.dispatch_due_reminders(actor_user_id=str(ctx.user.user_id), window_days=window_days)
    except MetrologyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="metrology_due_dispatch",
        event_type="update",
        resource_id="metrology_due_dispatch",
        before=None,
        after=result,
        meta={"window_days": window_days, "count": result["count"]},
    )
    return result


@router.get("/metrology/records/export")
def export_metrology_records(
    ctx: AuthContextDep,
    limit: int = 200,
    equipment_id: str | None = None,
    status: str | None = None,
):
    assert_capability(ctx, resource="metrology", action="record")
    service = _service_from_ctx(ctx)
    try:
        content = service.export_records_csv(limit=limit, equipment_id=equipment_id, status=status)
    except MetrologyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="metrology_record_export",
        event_type="export",
        resource_id="metrology_records",
        before=None,
        after={"limit": limit, "equipment_id": equipment_id, "status": status},
        meta={"line_count": max(0, len(content.splitlines()) - 1)},
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="metrology-records.csv"'},
    )

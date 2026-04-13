from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.services.maintenance import MaintenanceServiceError

router = APIRouter()


class MaintenanceRecordBody(BaseModel):
    equipment_id: str
    responsible_user_id: str
    maintenance_type: str
    planned_due_date: str
    summary: str
    performed_at_ms: int | None = None
    outcome_summary: str | None = None
    next_due_date: str | None = None
    attachments: list[dict] | None = None
    record_notes: str | None = None


class MaintenanceExecutionBody(BaseModel):
    performed_at_ms: int
    summary: str
    outcome_summary: str | None = None
    next_due_date: str | None = None
    attachments: list[dict] | None = None
    record_notes: str | None = None


class MaintenanceDecisionBody(BaseModel):
    notes: str | None = None


def _service_from_ctx(ctx: AuthContextDep):
    service = getattr(ctx.deps, "maintenance_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="maintenance_service_unavailable")
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
        source="maintenance",
        resource_type="maintenance_record",
        resource_id=resource_id,
        event_type=event_type,
        before=before,
        after=after,
        meta=meta or {},
    )


@router.post("/maintenance/records")
def create_maintenance_record(body: MaintenanceRecordBody, ctx: AuthContextDep, _: AdminOnly):
    _ensure_user_exists(ctx, body.responsible_user_id, field_name="responsible_user_id")
    service = _service_from_ctx(ctx)
    try:
        item = service.create_record(
            equipment_id=body.equipment_id,
            responsible_user_id=body.responsible_user_id,
            actor_user_id=str(ctx.user.user_id),
            maintenance_type=body.maintenance_type,
            planned_due_date=body.planned_due_date,
            summary=body.summary,
            performed_at_ms=body.performed_at_ms,
            outcome_summary=body.outcome_summary,
            next_due_date=body.next_due_date,
            attachments=body.attachments,
            record_notes=body.record_notes,
        )
    except MaintenanceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="maintenance_record_create",
        event_type="create",
        resource_id=item["record_id"],
        before=None,
        after=item,
        meta={"status": item["status"], "equipment_id": item["equipment_id"]},
    )
    return item


@router.get("/maintenance/records")
def list_maintenance_records(
    ctx: AuthContextDep,
    _: AdminOnly,
    limit: int = 100,
    equipment_id: str | None = None,
    status: str | None = None,
):
    service = _service_from_ctx(ctx)
    try:
        items = service.list_records(limit=limit, equipment_id=equipment_id, status=status)
    except MaintenanceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    return {"items": items, "count": len(items)}


@router.post("/maintenance/records/{record_id}/record")
def record_maintenance_execution(record_id: str, body: MaintenanceExecutionBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    before = service.get_record(record_id)
    try:
        item = service.record_execution(
            record_id=record_id,
            actor_user_id=str(ctx.user.user_id),
            performed_at_ms=body.performed_at_ms,
            summary=body.summary,
            outcome_summary=body.outcome_summary,
            next_due_date=body.next_due_date,
            attachments=body.attachments,
            record_notes=body.record_notes,
        )
    except MaintenanceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="maintenance_record_record",
        event_type="update",
        resource_id=item["record_id"],
        before=before,
        after=item,
        meta={"status": item["status"]},
    )
    return item


@router.post("/maintenance/records/{record_id}/approve")
def approve_maintenance_record(record_id: str, body: MaintenanceDecisionBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    before = service.get_record(record_id)
    try:
        item = service.approve_record(
            record_id=record_id,
            actor_user_id=str(ctx.user.user_id),
            approval_notes=body.notes,
        )
    except MaintenanceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="maintenance_record_approve",
        event_type="update",
        resource_id=item["record_id"],
        before=before,
        after=item,
        meta={"status": item["status"]},
    )
    return item


@router.post("/maintenance/reminders/dispatch")
def dispatch_maintenance_reminders(ctx: AuthContextDep, _: AdminOnly, window_days: int = 7):
    service = _service_from_ctx(ctx)
    try:
        result = service.dispatch_due_reminders(actor_user_id=str(ctx.user.user_id), window_days=window_days)
    except MaintenanceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="maintenance_due_dispatch",
        event_type="update",
        resource_id="maintenance_due_dispatch",
        before=None,
        after=result,
        meta={"window_days": window_days, "count": result["count"]},
    )
    return result


@router.get("/maintenance/records/export")
def export_maintenance_records(
    ctx: AuthContextDep,
    _: AdminOnly,
    limit: int = 200,
    equipment_id: str | None = None,
    status: str | None = None,
):
    service = _service_from_ctx(ctx)
    try:
        content = service.export_records_csv(limit=limit, equipment_id=equipment_id, status=status)
    except MaintenanceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="maintenance_record_export",
        event_type="export",
        resource_id="maintenance_records",
        before=None,
        after={"limit": limit, "equipment_id": equipment_id, "status": status},
        meta={"line_count": max(0, len(content.splitlines()) - 1)},
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="maintenance-records.csv"'},
    )

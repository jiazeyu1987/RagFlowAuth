from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep, assert_capability
from backend.services.equipment import EquipmentServiceError

router = APIRouter()


class EquipmentAssetBody(BaseModel):
    asset_code: str
    equipment_name: str
    owner_user_id: str
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    location: str | None = None
    supplier_name: str | None = None
    purchase_date: str | None = None
    retirement_due_date: str | None = None
    next_metrology_due_date: str | None = None
    next_maintenance_due_date: str | None = None
    notes: str | None = None


class EquipmentStatusBody(BaseModel):
    status_date: str | None = None
    notes: str | None = None


def _service_from_ctx(ctx: AuthContextDep):
    service = getattr(ctx.deps, "equipment_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="equipment_service_unavailable")
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
        source="equipment_lifecycle",
        resource_type="equipment_asset",
        resource_id=resource_id,
        event_type=event_type,
        before=before,
        after=after,
        meta=meta or {},
    )


@router.post("/equipment/assets")
def create_equipment_asset(body: EquipmentAssetBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="equipment_lifecycle", action="create")
    _ensure_user_exists(ctx, body.owner_user_id, field_name="owner_user_id")
    service = _service_from_ctx(ctx)
    try:
        item = service.create_asset(
            asset_code=body.asset_code,
            equipment_name=body.equipment_name,
            owner_user_id=body.owner_user_id,
            actor_user_id=str(ctx.user.user_id),
            manufacturer=body.manufacturer,
            model=body.model,
            serial_number=body.serial_number,
            location=body.location,
            supplier_name=body.supplier_name,
            purchase_date=body.purchase_date,
            retirement_due_date=body.retirement_due_date,
            next_metrology_due_date=body.next_metrology_due_date,
            next_maintenance_due_date=body.next_maintenance_due_date,
            notes=body.notes,
        )
    except EquipmentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="equipment_asset_create",
        event_type="create",
        resource_id=item["equipment_id"],
        before=None,
        after=item,
        meta={"status": item["status"], "owner_user_id": item["owner_user_id"]},
    )
    return item


@router.get("/equipment/assets")
def list_equipment_assets(
    ctx: AuthContextDep,
    limit: int = 100,
    status: str | None = None,
    owner_user_id: str | None = None,
):
    assert_capability(ctx, resource="equipment_lifecycle", action="maintain")
    service = _service_from_ctx(ctx)
    try:
        items = service.list_assets(limit=limit, status=status, owner_user_id=owner_user_id)
    except EquipmentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    return {"items": items, "count": len(items)}


@router.get("/equipment/assets/by-id/{equipment_id}")
def get_equipment_asset(equipment_id: str, ctx: AuthContextDep):
    assert_capability(ctx, resource="equipment_lifecycle", action="maintain")
    service = _service_from_ctx(ctx)
    try:
        return service.get_asset(equipment_id)
    except EquipmentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


def _transition_asset(equipment_id: str, body: EquipmentStatusBody, ctx: AuthContextDep, action: str):
    service = _service_from_ctx(ctx)
    before = service.get_asset(equipment_id)
    try:
        item = service.transition_status(
            equipment_id=equipment_id,
            action=action,
            actor_user_id=str(ctx.user.user_id),
            status_date=body.status_date,
            notes=body.notes,
        )
    except EquipmentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action=f"equipment_asset_{action}",
        event_type="update",
        resource_id=item["equipment_id"],
        before=before,
        after=item,
        meta={"status": item["status"]},
    )
    return item


@router.post("/equipment/assets/{equipment_id}/accept")
def accept_equipment_asset(equipment_id: str, body: EquipmentStatusBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="equipment_lifecycle", action="accept")
    return _transition_asset(equipment_id, body, ctx, "accept")


@router.post("/equipment/assets/{equipment_id}/commission")
def commission_equipment_asset(equipment_id: str, body: EquipmentStatusBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="equipment_lifecycle", action="accept")
    return _transition_asset(equipment_id, body, ctx, "commission")


@router.post("/equipment/assets/{equipment_id}/retire")
def retire_equipment_asset(equipment_id: str, body: EquipmentStatusBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="equipment_lifecycle", action="retire")
    return _transition_asset(equipment_id, body, ctx, "retire")


@router.post("/equipment/reminders/dispatch")
def dispatch_equipment_reminders(ctx: AuthContextDep, window_days: int = 7):
    assert_capability(ctx, resource="equipment_lifecycle", action="maintain")
    service = _service_from_ctx(ctx)
    try:
        result = service.dispatch_due_reminders(actor_user_id=str(ctx.user.user_id), window_days=window_days)
    except EquipmentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="equipment_due_dispatch",
        event_type="update",
        resource_id="equipment_due_dispatch",
        before=None,
        after=result,
        meta={"window_days": window_days, "count": result["count"]},
    )
    return result


@router.get("/equipment/assets/export")
def export_equipment_assets(
    ctx: AuthContextDep,
    limit: int = 200,
    status: str | None = None,
):
    assert_capability(ctx, resource="equipment_lifecycle", action="maintain")
    service = _service_from_ctx(ctx)
    try:
        content = service.export_assets_csv(limit=limit, status=status)
    except EquipmentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _audit(
        ctx,
        action="equipment_asset_export",
        event_type="export",
        resource_id="equipment_assets",
        before=None,
        after={"limit": limit, "status": status},
        meta={"line_count": max(0, len(content.splitlines()) - 1)},
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="equipment-assets.csv"'},
    )

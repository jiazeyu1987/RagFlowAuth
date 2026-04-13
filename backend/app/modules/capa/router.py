from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.services.governance_shared import GovernanceClosureError

router = APIRouter()


class CapaCreateBody(BaseModel):
    capa_code: str
    complaint_id: str | None = None
    action_title: str
    root_cause_summary: str
    correction_plan: str
    preventive_plan: str
    owner_user_id: str
    due_date: str


class CapaVerifyBody(BaseModel):
    effectiveness_summary: str


class CapaCloseBody(BaseModel):
    closure_summary: str


def _service_from_ctx(ctx: AuthContextDep):
    service = getattr(ctx.deps, "capa_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="capa_service_unavailable")
    return service


@router.post("/capa/actions")
def create_capa_action(body: CapaCreateBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    try:
        item = service.create_capa(
            capa_code=body.capa_code,
            complaint_id=body.complaint_id,
            action_title=body.action_title,
            root_cause_summary=body.root_cause_summary,
            correction_plan=body.correction_plan,
            preventive_plan=body.preventive_plan,
            owner_user_id=body.owner_user_id,
            due_date=body.due_date,
        )
    except GovernanceClosureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="audit_log_manager_unavailable")
    manager.log_ctx_event(
        ctx=ctx,
        action="capa_action_create",
        source="capa",
        resource_type="capa_action",
        resource_id=item["capa_id"],
        event_type="create",
        meta={
            "capa_code": item["capa_code"],
            "complaint_id": item["complaint_id"],
            "status": item["status"],
        },
    )
    return {"capa": item}


@router.get("/capa/actions")
def list_capa_actions(ctx: AuthContextDep, _: AdminOnly, status: str | None = None, limit: int = 100):
    service = _service_from_ctx(ctx)
    items = service.list_capas(status=status, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/capa/actions/{capa_id}/verify")
def verify_capa_action(capa_id: str, body: CapaVerifyBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    try:
        item = service.verify_capa(
            capa_id=capa_id,
            effectiveness_summary=body.effectiveness_summary,
            verified_by_user_id=str(ctx.user.user_id),
        )
    except GovernanceClosureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="audit_log_manager_unavailable")
    manager.log_ctx_event(
        ctx=ctx,
        action="capa_action_verify",
        source="capa",
        resource_type="capa_action",
        resource_id=item["capa_id"],
        event_type="update",
        meta={"status": item["status"]},
    )
    return {"capa": item}


@router.post("/capa/actions/{capa_id}/close")
def close_capa_action(capa_id: str, body: CapaCloseBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    try:
        item = service.close_capa(
            capa_id=capa_id,
            closed_by_user_id=str(ctx.user.user_id),
            closure_summary=body.closure_summary,
        )
    except GovernanceClosureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="audit_log_manager_unavailable")
    manager.log_ctx_event(
        ctx=ctx,
        action="capa_action_close",
        source="capa",
        resource_type="capa_action",
        resource_id=item["capa_id"],
        event_type="close",
        meta={"status": item["status"]},
    )
    return {"capa": item}

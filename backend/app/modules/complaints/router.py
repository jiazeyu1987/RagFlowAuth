from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep, assert_capability
from backend.services.governance_shared import GovernanceClosureError

router = APIRouter()


class ComplaintCreateBody(BaseModel):
    complaint_code: str
    source_channel: str
    severity_level: str
    subject: str
    description: str
    reported_by_user_id: str
    owner_user_id: str
    related_supplier_component_code: str | None = None
    related_environment_record_id: str | None = None
    received_at_ms: int | None = None


class ComplaintAssessBody(BaseModel):
    status: str
    disposition_summary: str
    linked_capa_id: str | None = None


class ComplaintCloseBody(BaseModel):
    closure_summary: str


def _service_from_ctx(ctx: AuthContextDep):
    service = getattr(ctx.deps, "complaint_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="complaint_service_unavailable")
    return service


@router.post("/complaints/cases")
def create_complaint_case(body: ComplaintCreateBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="complaints", action="create")
    service = _service_from_ctx(ctx)
    try:
        item = service.create_complaint(
            complaint_code=body.complaint_code,
            source_channel=body.source_channel,
            severity_level=body.severity_level,
            subject=body.subject,
            description=body.description,
            reported_by_user_id=body.reported_by_user_id,
            owner_user_id=body.owner_user_id,
            related_supplier_component_code=body.related_supplier_component_code,
            related_environment_record_id=body.related_environment_record_id,
            received_at_ms=body.received_at_ms,
        )
    except GovernanceClosureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="audit_log_manager_unavailable")
    manager.log_ctx_event(
        ctx=ctx,
        action="complaint_case_create",
        source="complaints",
        resource_type="complaint_case",
        resource_id=item["complaint_id"],
        event_type="create",
        meta={
            "complaint_code": item["complaint_code"],
            "source_channel": item["source_channel"],
            "severity_level": item["severity_level"],
            "status": item["status"],
        },
    )
    return {"complaint": item}


@router.get("/complaints/cases")
def list_complaint_cases(ctx: AuthContextDep, status: str | None = None, limit: int = 100):
    assert_capability(ctx, resource="complaints", action="view")
    service = _service_from_ctx(ctx)
    items = service.list_complaints(status=status, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/complaints/cases/{complaint_id}/assess")
def assess_complaint_case(complaint_id: str, body: ComplaintAssessBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="complaints", action="assess")
    service = _service_from_ctx(ctx)
    try:
        item = service.assess_complaint(
            complaint_id=complaint_id,
            status=body.status,
            disposition_summary=body.disposition_summary,
            linked_capa_id=body.linked_capa_id,
        )
    except GovernanceClosureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="audit_log_manager_unavailable")
    manager.log_ctx_event(
        ctx=ctx,
        action="complaint_case_assess",
        source="complaints",
        resource_type="complaint_case",
        resource_id=item["complaint_id"],
        event_type="update",
        meta={
            "status": item["status"],
            "linked_capa_id": item["linked_capa_id"],
        },
    )
    return {"complaint": item}


@router.post("/complaints/cases/{complaint_id}/close")
def close_complaint_case(complaint_id: str, body: ComplaintCloseBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="complaints", action="close")
    service = _service_from_ctx(ctx)
    try:
        item = service.close_complaint(
            complaint_id=complaint_id,
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
        action="complaint_case_close",
        source="complaints",
        resource_type="complaint_case",
        resource_id=item["complaint_id"],
        event_type="close",
        meta={"status": item["status"]},
    )
    return {"complaint": item}

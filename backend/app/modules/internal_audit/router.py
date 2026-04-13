from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.services.governance_shared import GovernanceClosureError

router = APIRouter()


class InternalAuditCreateBody(BaseModel):
    audit_code: str
    scope_summary: str
    lead_auditor_user_id: str
    planned_at_ms: int


class InternalAuditCompleteBody(BaseModel):
    findings_summary: str
    conclusion_summary: str
    related_capa_id: str | None = None


def _service_from_ctx(ctx: AuthContextDep):
    service = getattr(ctx.deps, "internal_audit_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="internal_audit_service_unavailable")
    return service


@router.post("/internal-audits/records")
def create_internal_audit_record(body: InternalAuditCreateBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    try:
        item = service.create_record(
            audit_code=body.audit_code,
            scope_summary=body.scope_summary,
            lead_auditor_user_id=body.lead_auditor_user_id,
            planned_at_ms=body.planned_at_ms,
        )
    except GovernanceClosureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="audit_log_manager_unavailable")
    manager.log_ctx_event(
        ctx=ctx,
        action="internal_audit_record_create",
        source="internal_audit",
        resource_type="internal_audit_record",
        resource_id=item["audit_id"],
        event_type="create",
        meta={
            "audit_code": item["audit_code"],
            "status": item["status"],
            "planned_at_ms": item["planned_at_ms"],
        },
    )
    return {"audit_record": item}


@router.get("/internal-audits/records")
def list_internal_audit_records(ctx: AuthContextDep, _: AdminOnly, status: str | None = None, limit: int = 100):
    service = _service_from_ctx(ctx)
    items = service.list_records(status=status, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/internal-audits/records/{audit_id}/complete")
def complete_internal_audit_record(audit_id: str, body: InternalAuditCompleteBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    try:
        item = service.complete_record(
            audit_id=audit_id,
            findings_summary=body.findings_summary,
            conclusion_summary=body.conclusion_summary,
            related_capa_id=body.related_capa_id,
            completed_by_user_id=str(ctx.user.user_id),
        )
    except GovernanceClosureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="audit_log_manager_unavailable")
    manager.log_ctx_event(
        ctx=ctx,
        action="internal_audit_record_complete",
        source="internal_audit",
        resource_type="internal_audit_record",
        resource_id=item["audit_id"],
        event_type="close",
        meta={"status": item["status"], "related_capa_id": item["related_capa_id"]},
    )
    return {"audit_record": item}

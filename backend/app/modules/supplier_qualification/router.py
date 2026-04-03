from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.services.supplier_qualification import SupplierQualificationError

router = APIRouter()


class SupplierComponentBody(BaseModel):
    component_code: str
    component_name: str
    supplier_name: str
    component_category: str
    deployment_scope: str
    current_version: str
    approved_version: str | None = None
    supplier_approval_status: str
    intended_use_summary: str
    qualification_summary: str
    supplier_audit_summary: str
    known_issue_review: str
    revalidation_trigger: str | None = None
    migration_plan_summary: str
    review_due_date: str | None = None


class SupplierComponentVersionChangeBody(BaseModel):
    new_version: str
    change_summary: str


class EnvironmentQualificationBody(BaseModel):
    component_code: str
    environment_name: str
    company_id: int | None = None
    release_version: str
    protocol_ref: str
    iq_status: str
    oq_status: str
    pq_status: str
    qualification_summary: str
    deviation_summary: str | None = None
    executed_by_user_id: str


def _service_from_ctx(ctx: AuthContextDep):
    service = getattr(ctx.deps, "supplier_qualification_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="supplier_qualification_service_unavailable")
    return service


def _ensure_user_exists(ctx: AuthContextDep, user_id: str, *, field_name: str) -> None:
    user = ctx.deps.user_store.get_by_user_id(str(user_id).strip())
    if user is None:
        raise HTTPException(status_code=400, detail=f"{field_name}_not_found")


@router.post("/supplier-qualifications/components")
def upsert_supplier_component(body: SupplierComponentBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    try:
        item = service.upsert_component(
            component_code=body.component_code,
            component_name=body.component_name,
            supplier_name=body.supplier_name,
            component_category=body.component_category,
            deployment_scope=body.deployment_scope,
            current_version=body.current_version,
            approved_version=body.approved_version,
            supplier_approval_status=body.supplier_approval_status,
            intended_use_summary=body.intended_use_summary,
            qualification_summary=body.qualification_summary,
            supplier_audit_summary=body.supplier_audit_summary,
            known_issue_review=body.known_issue_review,
            revalidation_trigger=body.revalidation_trigger,
            migration_plan_summary=body.migration_plan_summary,
            review_due_date=body.review_due_date,
            approved_by_user_id=(
                str(ctx.user.user_id)
                if str(body.supplier_approval_status).strip().lower() == "approved"
                else None
            ),
        )
    except SupplierQualificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is not None:
        manager.safe_log_ctx_event(
            ctx=ctx,
            action="supplier_component_upsert",
            source="supplier_qualification",
            resource_type="supplier_component",
            resource_id=item["component_code"],
            event_type="update",
            meta={
                "component_category": item["component_category"],
                "deployment_scope": item["deployment_scope"],
                "current_version": item["current_version"],
                "approved_version": item["approved_version"],
                "supplier_approval_status": item["supplier_approval_status"],
                "qualification_status": item["qualification_status"],
            },
        )
    return item


@router.get("/supplier-qualifications/components")
def list_supplier_components(ctx: AuthContextDep, _: AdminOnly, limit: int = 100):
    service = _service_from_ctx(ctx)
    items = service.list_components(limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/supplier-qualifications/components/{component_code}/version-change")
def record_component_version_change(
    component_code: str,
    body: SupplierComponentVersionChangeBody,
    ctx: AuthContextDep,
    _: AdminOnly,
):
    service = _service_from_ctx(ctx)
    try:
        item = service.record_version_change(
            component_code=component_code,
            new_version=body.new_version,
            change_summary=body.change_summary,
        )
    except SupplierQualificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is not None:
        manager.safe_log_ctx_event(
            ctx=ctx,
            action="supplier_component_version_change",
            source="supplier_qualification",
            resource_type="supplier_component",
            resource_id=item["component_code"],
            event_type="update",
            reason=body.change_summary,
            meta={
                "new_version": item["current_version"],
                "approved_version": item["approved_version"],
                "qualification_status": item["qualification_status"],
                "revalidation_trigger": item["revalidation_trigger"],
            },
        )
    return item


@router.post("/supplier-qualifications/environment-records")
def record_environment_qualification(body: EnvironmentQualificationBody, ctx: AuthContextDep, _: AdminOnly):
    _ensure_user_exists(ctx, body.executed_by_user_id, field_name="executed_by_user_id")
    service = _service_from_ctx(ctx)
    try:
        item = service.record_environment_qualification(
            component_code=body.component_code,
            environment_name=body.environment_name,
            company_id=body.company_id,
            release_version=body.release_version,
            protocol_ref=body.protocol_ref,
            iq_status=body.iq_status,
            oq_status=body.oq_status,
            pq_status=body.pq_status,
            qualification_summary=body.qualification_summary,
            deviation_summary=body.deviation_summary,
            executed_by_user_id=body.executed_by_user_id,
            approved_by_user_id=(str(ctx.user.user_id) if str(ctx.user.user_id).strip() else None),
        )
    except SupplierQualificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is not None:
        manager.safe_log_ctx_event(
            ctx=ctx,
            action="environment_qualification_record",
            source="supplier_qualification",
            resource_type="environment_qualification",
            resource_id=item["record_id"],
            event_type="create",
            meta={
                "component_code": item["component_code"],
                "environment_name": item["environment_name"],
                "company_id": item["company_id"],
                "release_version": item["release_version"],
                "iq_status": item["iq_status"],
                "oq_status": item["oq_status"],
                "pq_status": item["pq_status"],
                "qualification_status": item["qualification_status"],
            },
        )
    return item


@router.get("/supplier-qualifications/environment-records")
def list_environment_qualification_records(
    ctx: AuthContextDep,
    _: AdminOnly,
    limit: int = 100,
    component_code: str | None = None,
):
    service = _service_from_ctx(ctx)
    items = service.list_environment_records(limit=limit, component_code=component_code)
    return {"items": items, "count": len(items)}

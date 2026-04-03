from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.core.training_support import resolve_training_compliance_service
from backend.services.training_compliance import TrainingComplianceError

router = APIRouter()


class TrainingRequirementBody(BaseModel):
    requirement_code: str
    requirement_name: str
    role_code: str
    controlled_action: str
    curriculum_version: str
    training_material_ref: str
    effectiveness_required: bool = True
    recertification_interval_days: int
    review_due_date: str | None = None
    active: bool = True


class TrainingRecordBody(BaseModel):
    requirement_code: str
    user_id: str
    curriculum_version: str
    trainer_user_id: str
    training_outcome: str
    effectiveness_status: str
    effectiveness_score: float | None = None
    effectiveness_summary: str
    training_notes: str | None = None
    completed_at_ms: int | None = None
    effectiveness_reviewed_by_user_id: str | None = None
    effectiveness_reviewed_at_ms: int | None = None


class OperatorCertificationBody(BaseModel):
    requirement_code: str
    user_id: str
    granted_by_user_id: str | None = None
    certification_status: str = "active"
    valid_until_ms: int | None = None
    exception_release_ref: str | None = None
    certification_notes: str | None = None
    granted_at_ms: int | None = None


def _service_from_ctx(ctx: AuthContextDep):
    return resolve_training_compliance_service(ctx.deps)


def _ensure_user_exists(ctx: AuthContextDep, user_id: str, *, field_name: str):
    user = ctx.deps.user_store.get_by_user_id(str(user_id).strip())
    if user is None:
        raise HTTPException(status_code=400, detail=f"{field_name}_not_found")
    return user


@router.post("/training-compliance/requirements")
def upsert_training_requirement(body: TrainingRequirementBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    try:
        item = service.upsert_requirement(
            requirement_code=body.requirement_code,
            requirement_name=body.requirement_name,
            role_code=body.role_code,
            controlled_action=body.controlled_action,
            curriculum_version=body.curriculum_version,
            training_material_ref=body.training_material_ref,
            effectiveness_required=body.effectiveness_required,
            recertification_interval_days=body.recertification_interval_days,
            review_due_date=body.review_due_date,
            active=body.active,
        )
    except TrainingComplianceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is not None:
        manager.safe_log_ctx_event(
            ctx=ctx,
            action="training_requirement_upsert",
            source="training_compliance",
            resource_type="training_requirement",
            resource_id=item["requirement_code"],
            event_type="update",
            meta={
                "role_code": item["role_code"],
                "controlled_action": item["controlled_action"],
                "curriculum_version": item["curriculum_version"],
                "active": item["active"],
            },
        )
    return item


@router.get("/training-compliance/requirements")
def list_training_requirements(
    ctx: AuthContextDep,
    _: AdminOnly,
    limit: int = 100,
    controlled_action: str | None = None,
    role_code: str | None = None,
):
    service = _service_from_ctx(ctx)
    items = service.list_requirements(limit=limit, controlled_action=controlled_action, role_code=role_code)
    return {"items": items, "count": len(items)}


@router.post("/training-compliance/records")
def create_training_record(body: TrainingRecordBody, ctx: AuthContextDep, _: AdminOnly):
    _ensure_user_exists(ctx, body.user_id, field_name="user_id")
    _ensure_user_exists(ctx, body.trainer_user_id, field_name="trainer_user_id")
    if body.effectiveness_reviewed_by_user_id:
        _ensure_user_exists(
            ctx,
            body.effectiveness_reviewed_by_user_id,
            field_name="effectiveness_reviewed_by_user_id",
        )
    service = _service_from_ctx(ctx)
    try:
        item = service.record_training(
            requirement_code=body.requirement_code,
            user_id=body.user_id,
            curriculum_version=body.curriculum_version,
            trainer_user_id=body.trainer_user_id,
            training_outcome=body.training_outcome,
            effectiveness_status=body.effectiveness_status,
            effectiveness_score=body.effectiveness_score,
            effectiveness_summary=body.effectiveness_summary,
            training_notes=body.training_notes,
            completed_at_ms=body.completed_at_ms,
            effectiveness_reviewed_by_user_id=body.effectiveness_reviewed_by_user_id,
            effectiveness_reviewed_at_ms=body.effectiveness_reviewed_at_ms,
        )
    except TrainingComplianceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is not None:
        manager.safe_log_ctx_event(
            ctx=ctx,
            action="training_record_create",
            source="training_compliance",
            resource_type="training_record",
            resource_id=item["record_id"],
            event_type="create",
            meta={
                "requirement_code": item["requirement_code"],
                "user_id": item["user_id"],
                "curriculum_version": item["curriculum_version"],
                "training_outcome": item["training_outcome"],
                "effectiveness_status": item["effectiveness_status"],
            },
        )
    return item


@router.get("/training-compliance/records")
def list_training_records(
    ctx: AuthContextDep,
    _: AdminOnly,
    limit: int = 100,
    requirement_code: str | None = None,
    user_id: str | None = None,
):
    service = _service_from_ctx(ctx)
    items = service.list_training_records(limit=limit, requirement_code=requirement_code, user_id=user_id)
    return {"items": items, "count": len(items)}


@router.post("/training-compliance/certifications")
def create_operator_certification(body: OperatorCertificationBody, ctx: AuthContextDep, _: AdminOnly):
    _ensure_user_exists(ctx, body.user_id, field_name="user_id")
    granted_by_user_id = body.granted_by_user_id or str(ctx.user.user_id)
    _ensure_user_exists(ctx, granted_by_user_id, field_name="granted_by_user_id")
    service = _service_from_ctx(ctx)
    try:
        item = service.grant_certification(
            requirement_code=body.requirement_code,
            user_id=body.user_id,
            granted_by_user_id=granted_by_user_id,
            certification_status=body.certification_status,
            valid_until_ms=body.valid_until_ms,
            exception_release_ref=body.exception_release_ref,
            certification_notes=body.certification_notes,
            granted_at_ms=body.granted_at_ms,
        )
    except TrainingComplianceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is not None:
        manager.safe_log_ctx_event(
            ctx=ctx,
            action="operator_certification_create",
            source="training_compliance",
            resource_type="operator_certification",
            resource_id=item["certification_id"],
            event_type="create",
            meta={
                "requirement_code": item["requirement_code"],
                "user_id": item["user_id"],
                "curriculum_version": item["curriculum_version"],
                "certification_status": item["certification_status"],
                "valid_until_ms": item["valid_until_ms"],
            },
        )
    return item


@router.get("/training-compliance/certifications")
def list_operator_certifications(
    ctx: AuthContextDep,
    _: AdminOnly,
    limit: int = 100,
    requirement_code: str | None = None,
    user_id: str | None = None,
):
    service = _service_from_ctx(ctx)
    items = service.list_certifications(limit=limit, requirement_code=requirement_code, user_id=user_id)
    return {"items": items, "count": len(items)}


@router.get("/training-compliance/actions/{controlled_action}/users/{user_id}")
def get_action_training_status(
    controlled_action: str,
    user_id: str,
    ctx: AuthContextDep,
    _: AdminOnly,
):
    user = _ensure_user_exists(ctx, user_id, field_name="user_id")
    service = _service_from_ctx(ctx)
    try:
        return service.evaluate_action_status(
            user_id=str(user.user_id),
            role_code=str(getattr(user, "role", "") or ""),
            controlled_action=controlled_action,
        )
    except TrainingComplianceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.services.emergency_change import EmergencyChangeServiceError

router = APIRouter()


class EmergencyChangeCreateBody(BaseModel):
    title: str
    summary: str
    authorizer_user_id: str
    reviewer_user_id: str
    authorization_basis: str
    risk_assessment: str
    risk_control: str
    rollback_plan: str
    training_notification_plan: str


class EmergencyChangeAuthorizeBody(BaseModel):
    authorization_notes: str | None = None


class EmergencyChangeDeployBody(BaseModel):
    deployment_summary: str


class EmergencyChangeCloseBody(BaseModel):
    impact_assessment_summary: str
    post_review_summary: str
    capa_actions: str
    verification_summary: str


def _service_from_ctx(ctx: AuthContextDep):
    service = getattr(ctx.deps, "emergency_change_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="emergency_change_service_unavailable")
    return service


@router.post("/emergency-changes")
def create_emergency_change(body: EmergencyChangeCreateBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    try:
        return service.create_change(
            title=body.title,
            summary=body.summary,
            requested_by_user_id=str(ctx.user.user_id),
            authorizer_user_id=body.authorizer_user_id,
            reviewer_user_id=body.reviewer_user_id,
            authorization_basis=body.authorization_basis,
            risk_assessment=body.risk_assessment,
            risk_control=body.risk_control,
            rollback_plan=body.rollback_plan,
            training_notification_plan=body.training_notification_plan,
        )
    except EmergencyChangeServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.get("/emergency-changes")
def list_emergency_changes(ctx: AuthContextDep, _: AdminOnly, limit: int = 100, status: str | None = None):
    service = _service_from_ctx(ctx)
    items = service.list_changes(limit=limit, status=status)
    return {"items": items, "count": len(items)}


@router.get("/emergency-changes/{change_id}")
def get_emergency_change(change_id: str, ctx: AuthContextDep):
    service = _service_from_ctx(ctx)
    try:
        item = service.get_change(change_id)
    except EmergencyChangeServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    current_user_id = str(ctx.user.user_id)
    is_admin = bool(ctx.snapshot.is_admin)
    participants = {
        str(item["requested_by_user_id"]),
        str(item["authorizer_user_id"]),
        str(item["reviewer_user_id"]),
    }
    if not is_admin and current_user_id not in participants:
        raise HTTPException(status_code=403, detail="emergency_change_access_denied")
    return item


@router.post("/emergency-changes/{change_id}/authorize")
def authorize_emergency_change(change_id: str, body: EmergencyChangeAuthorizeBody, ctx: AuthContextDep):
    service = _service_from_ctx(ctx)
    try:
        return service.authorize_change(
            change_id=change_id,
            actor_user_id=str(ctx.user.user_id),
            authorization_notes=body.authorization_notes,
        )
    except EmergencyChangeServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.post("/emergency-changes/{change_id}/deploy")
def deploy_emergency_change(change_id: str, body: EmergencyChangeDeployBody, ctx: AuthContextDep, _: AdminOnly):
    service = _service_from_ctx(ctx)
    try:
        return service.deploy_change(
            change_id=change_id,
            actor_user_id=str(ctx.user.user_id),
            deployment_summary=body.deployment_summary,
        )
    except EmergencyChangeServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.post("/emergency-changes/{change_id}/close")
def close_emergency_change(change_id: str, body: EmergencyChangeCloseBody, ctx: AuthContextDep):
    service = _service_from_ctx(ctx)
    try:
        return service.close_change(
            change_id=change_id,
            actor_user_id=str(ctx.user.user_id),
            impact_assessment_summary=body.impact_assessment_summary,
            post_review_summary=body.post_review_summary,
            capa_actions=body.capa_actions,
            verification_summary=body.verification_summary,
        )
    except EmergencyChangeServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

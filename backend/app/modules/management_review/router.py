from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep, assert_capability
from backend.services.governance_shared import GovernanceClosureError

router = APIRouter()


class ManagementReviewCreateBody(BaseModel):
    review_code: str
    meeting_at_ms: int
    chair_user_id: str
    input_summary: str


class ManagementReviewCompleteBody(BaseModel):
    output_summary: str
    decision_summary: str
    follow_up_capa_id: str | None = None


def _service_from_ctx(ctx: AuthContextDep):
    service = getattr(ctx.deps, "management_review_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="management_review_service_unavailable")
    return service


@router.post("/management-reviews/records")
def create_management_review_record(body: ManagementReviewCreateBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="management_review", action="create")
    service = _service_from_ctx(ctx)
    try:
        item = service.create_record(
            review_code=body.review_code,
            meeting_at_ms=body.meeting_at_ms,
            chair_user_id=body.chair_user_id,
            input_summary=body.input_summary,
        )
    except GovernanceClosureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="audit_log_manager_unavailable")
    manager.log_ctx_event(
        ctx=ctx,
        action="management_review_record_create",
        source="management_review",
        resource_type="management_review_record",
        resource_id=item["review_id"],
        event_type="create",
        meta={
            "review_code": item["review_code"],
            "status": item["status"],
            "meeting_at_ms": item["meeting_at_ms"],
        },
    )
    return {"management_review": item}


@router.get("/management-reviews/records")
def list_management_review_records(ctx: AuthContextDep, status: str | None = None, limit: int = 100):
    assert_capability(ctx, resource="management_review", action="view")
    service = _service_from_ctx(ctx)
    items = service.list_records(status=status, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/management-reviews/records/{review_id}/complete")
def complete_management_review_record(
    review_id: str,
    body: ManagementReviewCompleteBody,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="management_review", action="complete")
    service = _service_from_ctx(ctx)
    try:
        item = service.complete_record(
            review_id=review_id,
            output_summary=body.output_summary,
            decision_summary=body.decision_summary,
            follow_up_capa_id=body.follow_up_capa_id,
            completed_by_user_id=str(ctx.user.user_id),
        )
    except GovernanceClosureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="audit_log_manager_unavailable")
    manager.log_ctx_event(
        ctx=ctx,
        action="management_review_record_complete",
        source="management_review",
        resource_type="management_review_record",
        resource_id=item["review_id"],
        event_type="close",
        meta={"status": item["status"], "follow_up_capa_id": item["follow_up_capa_id"]},
    )
    return {"management_review": item}

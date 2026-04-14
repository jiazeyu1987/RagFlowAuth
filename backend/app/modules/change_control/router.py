from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep, assert_capability
from backend.services.change_control import ChangeControlServiceError

router = APIRouter()


class ChangeRequestCreateBody(BaseModel):
    title: str
    reason: str
    owner_user_id: str
    evaluator_user_id: str
    planned_due_date: str | None = None
    required_departments: list[str] = []
    affected_controlled_revisions: list[str] = []


class ChangeEvaluationBody(BaseModel):
    evaluation_summary: str


class ChangePlanItemCreateBody(BaseModel):
    title: str
    assignee_user_id: str
    due_date: str


class ChangePlanItemStatusBody(BaseModel):
    status: str
    completion_note: str | None = None


class ChangePlanConfirmBody(BaseModel):
    plan_summary: str


class ChangeExecutionCompleteBody(BaseModel):
    execution_summary: str


class ChangeConfirmationBody(BaseModel):
    department_code: str
    notes: str | None = None


class ChangeCloseBody(BaseModel):
    close_summary: str
    close_outcome: str
    ledger_writeback_ref: str
    closed_controlled_revisions: list[str]


def _service_from_ctx(ctx: AuthContextDep):
    service = getattr(ctx.deps, "change_control_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="change_control_service_unavailable")
    return service


def _as_http_error(exc: ChangeControlServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.code)


def _is_admin(ctx: AuthContextDep) -> bool:
    return bool(getattr(ctx.snapshot, "is_admin", False))


@router.post("/change-control/requests")
def create_change_request(body: ChangeRequestCreateBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="change_control", action="create")
    service = _service_from_ctx(ctx)
    try:
        return service.create_request(
            title=body.title,
            reason=body.reason,
            requester_user_id=str(ctx.user.user_id),
            owner_user_id=body.owner_user_id,
            evaluator_user_id=body.evaluator_user_id,
            planned_due_date=body.planned_due_date,
            required_departments=body.required_departments,
            affected_controlled_revisions=body.affected_controlled_revisions,
        )
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc


@router.get("/change-control/requests")
def list_change_requests(ctx: AuthContextDep, limit: int = 100, status: str | None = None):
    assert_capability(ctx, resource="change_control", action="evaluate")
    service = _service_from_ctx(ctx)
    items = service.list_requests(limit=limit, status=status)
    return {"items": items, "count": len(items)}


@router.get("/change-control/requests/{request_id}")
def get_change_request(request_id: str, ctx: AuthContextDep):
    service = _service_from_ctx(ctx)
    try:
        item = service.get_request(request_id)
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc
    participants = {
        str(item["requester_user_id"]),
        str(item["owner_user_id"]),
        str(item["evaluator_user_id"]),
    }
    if str(ctx.user.user_id) not in participants:
        assert_capability(ctx, resource="change_control", action="evaluate")
    return item


@router.post("/change-control/requests/{request_id}/evaluate")
def evaluate_change_request(request_id: str, body: ChangeEvaluationBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="change_control", action="evaluate")
    service = _service_from_ctx(ctx)
    try:
        return service.evaluate_request(
            request_id=request_id,
            actor_user_id=str(ctx.user.user_id),
            is_admin=_is_admin(ctx),
            evaluation_summary=body.evaluation_summary,
        )
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc


@router.post("/change-control/requests/{request_id}/plan-items")
def create_change_plan_item(request_id: str, body: ChangePlanItemCreateBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="change_control", action="plan")
    service = _service_from_ctx(ctx)
    try:
        return service.create_plan_item(
            request_id=request_id,
            actor_user_id=str(ctx.user.user_id),
            is_admin=_is_admin(ctx),
            title=body.title,
            assignee_user_id=body.assignee_user_id,
            due_date=body.due_date,
        )
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc


@router.patch("/change-control/requests/{request_id}/plan-items/{plan_item_id}")
def update_change_plan_item_status(
    request_id: str,
    plan_item_id: str,
    body: ChangePlanItemStatusBody,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="change_control", action="plan")
    service = _service_from_ctx(ctx)
    try:
        return service.update_plan_item_status(
            request_id=request_id,
            plan_item_id=plan_item_id,
            actor_user_id=str(ctx.user.user_id),
            is_admin=_is_admin(ctx),
            status=body.status,
            completion_note=body.completion_note,
        )
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc


@router.post("/change-control/requests/{request_id}/plan")
def mark_change_request_planned(request_id: str, body: ChangePlanConfirmBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="change_control", action="plan")
    service = _service_from_ctx(ctx)
    try:
        return service.mark_planned(
            request_id=request_id,
            actor_user_id=str(ctx.user.user_id),
            is_admin=_is_admin(ctx),
            plan_summary=body.plan_summary,
        )
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc


@router.post("/change-control/requests/{request_id}/start-execution")
def start_change_request_execution(request_id: str, ctx: AuthContextDep):
    assert_capability(ctx, resource="change_control", action="plan")
    service = _service_from_ctx(ctx)
    try:
        return service.start_execution(
            request_id=request_id,
            actor_user_id=str(ctx.user.user_id),
            is_admin=_is_admin(ctx),
        )
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc


@router.post("/change-control/requests/{request_id}/complete-execution")
def complete_change_request_execution(request_id: str, body: ChangeExecutionCompleteBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="change_control", action="plan")
    service = _service_from_ctx(ctx)
    try:
        return service.complete_execution(
            request_id=request_id,
            actor_user_id=str(ctx.user.user_id),
            is_admin=_is_admin(ctx),
            execution_summary=body.execution_summary,
        )
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc


@router.post("/change-control/requests/{request_id}/confirmations")
def confirm_change_request_department(request_id: str, body: ChangeConfirmationBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="change_control", action="confirm")
    service = _service_from_ctx(ctx)
    try:
        return service.confirm_department(
            request_id=request_id,
            actor_user_id=str(ctx.user.user_id),
            department_code=body.department_code,
            notes=body.notes,
        )
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc


@router.post("/change-control/reminders/dispatch")
def dispatch_change_request_reminders(ctx: AuthContextDep, window_days: int = 7):
    assert_capability(ctx, resource="change_control", action="plan")
    service = _service_from_ctx(ctx)
    try:
        return service.dispatch_due_reminders(actor_user_id=str(ctx.user.user_id), window_days=window_days)
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc


@router.post("/change-control/requests/{request_id}/close")
def close_change_request(request_id: str, body: ChangeCloseBody, ctx: AuthContextDep):
    assert_capability(ctx, resource="change_control", action="close")
    service = _service_from_ctx(ctx)
    try:
        return service.close_request(
            request_id=request_id,
            actor_user_id=str(ctx.user.user_id),
            is_admin=_is_admin(ctx),
            close_summary=body.close_summary,
            close_outcome=body.close_outcome,
            ledger_writeback_ref=body.ledger_writeback_ref,
            closed_controlled_revisions=body.closed_controlled_revisions,
        )
    except ChangeControlServiceError as exc:
        raise _as_http_error(exc) from exc

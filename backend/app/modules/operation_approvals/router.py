from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.core.training_support import assert_user_training_for_action
from backend.models.operation_approval import (
    OperationApprovalActionBody,
    OperationApprovalActionResultEnvelope,
    OperationApprovalRequestBrief,
    OperationApprovalWithdrawBody,
    OperationApprovalWorkflowResultEnvelope,
    OperationApprovalWorkflowBody,
)
from backend.services.operation_approval import OperationApprovalServiceError


router = APIRouter()


def _service(ctx: AuthContextDep):
    service = getattr(ctx.deps, "operation_approval_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="operation_approval_service_unavailable")
    return service


def _wrap_workflow_result(*, workflow: dict, message: str) -> dict[str, dict[str, str]]:
    return {
        "result": {
            "message": message,
            "operation_type": str(workflow["operation_type"]),
        }
    }


def _wrap_request_result(*, request_data: dict, message: str) -> dict[str, dict[str, str]]:
    return {
        "result": {
            "message": message,
            "request_id": str(request_data["request_id"]),
            "status": str(request_data["status"]),
        }
    }


@router.get("/operation-approvals/workflows")
def list_operation_approval_workflows(ctx: AuthContextDep, _: AdminOnly):
    items = _service(ctx).list_workflows()
    return {"items": items, "count": len(items)}


@router.put("/operation-approvals/workflows/{operation_type}", response_model=OperationApprovalWorkflowResultEnvelope)
def upsert_operation_approval_workflow(
    operation_type: str,
    body: OperationApprovalWorkflowBody,
    ctx: AuthContextDep,
    _: AdminOnly,
):
    try:
        workflow = _service(ctx).upsert_workflow(
            operation_type=operation_type,
            name=body.name,
            steps=[item.model_dump() for item in body.steps],
        )
        return _wrap_workflow_result(
            workflow=workflow,
            message="operation_approval_workflow_updated",
        )
    except OperationApprovalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.get("/operation-approvals/requests")
def list_operation_approval_requests(
    ctx: AuthContextDep,
    view: str = Query(default="mine"),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        return _service(ctx).list_requests_for_user(requester_user=ctx.user, view=view, status=status, limit=limit)
    except OperationApprovalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.get("/operation-approvals/requests/{request_id}")
def get_operation_approval_request(request_id: str, ctx: AuthContextDep):
    try:
        return _service(ctx).get_request_detail_for_user(request_id=request_id, requester_user=ctx.user)
    except OperationApprovalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.get("/operation-approvals/stats")
def get_operation_approval_stats(ctx: AuthContextDep):
    try:
        return _service(ctx).get_stats_for_user(requester_user=ctx.user)
    except OperationApprovalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.post(
    "/operation-approvals/requests/{request_id}/approve",
    response_model=OperationApprovalActionResultEnvelope,
)
def approve_operation_approval_request(request_id: str, body: OperationApprovalActionBody, ctx: AuthContextDep):
    try:
        assert_user_training_for_action(deps=ctx.deps, user=ctx.user, controlled_action="document_review")
        request_data = _service(ctx).approve_request(
            request_id=request_id,
            actor_user=ctx.user,
            sign_token=body.sign_token,
            signature_meaning=body.signature_meaning,
            signature_reason=body.signature_reason,
            notes=body.notes,
        )
        return _wrap_request_result(
            request_data=request_data,
            message="operation_approval_request_approved",
        )
    except OperationApprovalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.post(
    "/operation-approvals/requests/{request_id}/reject",
    response_model=OperationApprovalActionResultEnvelope,
)
def reject_operation_approval_request(request_id: str, body: OperationApprovalActionBody, ctx: AuthContextDep):
    try:
        assert_user_training_for_action(deps=ctx.deps, user=ctx.user, controlled_action="document_review")
        request_data = _service(ctx).reject_request(
            request_id=request_id,
            actor_user=ctx.user,
            sign_token=body.sign_token,
            signature_meaning=body.signature_meaning,
            signature_reason=body.signature_reason,
            notes=body.notes,
        )
        return _wrap_request_result(
            request_data=request_data,
            message="operation_approval_request_rejected",
        )
    except OperationApprovalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.post(
    "/operation-approvals/requests/{request_id}/withdraw",
    response_model=OperationApprovalActionResultEnvelope,
)
def withdraw_operation_approval_request(request_id: str, body: OperationApprovalWithdrawBody, ctx: AuthContextDep):
    try:
        request_data = _service(ctx).withdraw_request(
            request_id=request_id,
            actor_user=ctx.user,
            reason=body.reason,
        )
        return _wrap_request_result(
            request_data=request_data,
            message="operation_approval_request_withdrawn",
        )
    except OperationApprovalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.get("/operation-approvals/todos")
def list_operation_approval_todos(
    ctx: AuthContextDep,
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        return _service(ctx).list_todos_for_user(requester_user=ctx.user, limit=limit)
    except OperationApprovalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

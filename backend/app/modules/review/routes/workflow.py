from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.core.permission_resolver import ResourceScope, assert_can_review
from backend.services.approval import ApprovalWorkflowError, ApprovalWorkflowService, ApprovalWorkflowStore


router = APIRouter()


class WorkflowStepBody(BaseModel):
    step_no: int
    step_name: str
    approver_user_id: str | None = None
    approver_role: str | None = None
    approver_group_id: int | None = None
    approver_department_id: int | None = None
    approver_company_id: int | None = None
    approval_mode: str = "all"


class WorkflowUpsertBody(BaseModel):
    kb_ref: str
    name: str
    steps: list[WorkflowStepBody]


def _resolve_workflow_service(ctx: AuthContextDep) -> ApprovalWorkflowService:
    deps = ctx.deps
    service = getattr(deps, "approval_workflow_service", None)
    if service is not None:
        return service
    kb_store = getattr(deps, "kb_store", None)
    db_path = getattr(kb_store, "db_path", None)
    if not db_path:
        raise HTTPException(status_code=500, detail="approval_workflow_service_unavailable")
    notification_service = getattr(deps, "notification_service", None)
    return ApprovalWorkflowService(
        store=ApprovalWorkflowStore(db_path=str(db_path)),
        notification_service=notification_service,
    )


@router.get("/review/workflows")
def list_workflows(ctx: AuthContextDep, _: AdminOnly, kb_ref: str | None = None):
    service = _resolve_workflow_service(ctx)
    items = service.list_workflows(kb_ref=kb_ref)
    return {"items": items, "count": len(items)}


@router.get("/review/pending-approvals")
def list_my_pending_approvals(ctx: AuthContextDep, limit: int = 100):
    assert_can_review(ctx.snapshot)
    kb_refs: list[str] | None = None
    if ctx.snapshot.kb_scope == ResourceScope.NONE:
        return {"items": [], "count": 0}
    if ctx.snapshot.kb_scope != ResourceScope.ALL:
        kb_refs = sorted(ctx.snapshot.kb_names)
    docs = ctx.deps.kb_store.list_documents(status="pending", kb_refs=kb_refs, limit=limit)
    service = _resolve_workflow_service(ctx)
    items = service.get_pending_reviews_for_user(docs=docs, user=ctx.user)
    return {"items": items, "count": len(items)}


@router.put("/review/workflows/{workflow_id}")
def upsert_workflow(workflow_id: str, body: WorkflowUpsertBody, ctx: AuthContextDep, _: AdminOnly):
    service = _resolve_workflow_service(ctx)
    try:
        item = service.upsert_workflow(
            workflow_id=workflow_id,
            kb_ref=body.kb_ref,
            name=body.name,
            steps=[x.model_dump() for x in body.steps],
        )
    except ApprovalWorkflowError as e:
        raise HTTPException(status_code=e.status_code, detail=e.code) from e
    return item

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep, assert_capability
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import ResourceScope, assert_kb_allowed
from backend.services.document_control import DocumentControlError, DocumentControlService


router = APIRouter()


class RevisionWorkflowActionRequest(BaseModel):
    note: str | None = None


class RevisionAddSignRequest(BaseModel):
    approver_user_id: str
    note: str | None = None


class RevisionPublishRequest(BaseModel):
    release_mode: str
    note: str | None = None


class DistributionDepartmentsRequest(BaseModel):
    department_ids: list[int]


class DepartmentAckConfirmRequest(BaseModel):
    notes: str | None = None


class ObsoleteInitiateRequest(BaseModel):
    retirement_reason: str
    retention_until_ms: int
    note: str | None = None


class DestructionConfirmRequest(BaseModel):
    destruction_notes: str


class DocumentControlWorkflowStepRequest(BaseModel):
    step_type: str
    approval_rule: str
    approver_user_ids: list[str]
    timeout_reminder_minutes: int
    member_source: str | None = None


class DocumentControlWorkflowRequest(BaseModel):
    name: str | None = None
    steps: list[DocumentControlWorkflowStepRequest]


class DocumentControlWorkflowStepRequest(BaseModel):
    step_type: str
    approval_rule: str
    approver_user_ids: list[str]
    timeout_reminder_minutes: int
    member_source: str | None = None


class DocumentControlWorkflowRequest(BaseModel):
    name: str | None = None
    steps: list[DocumentControlWorkflowStepRequest]


def _service(ctx: AuthContextDep) -> DocumentControlService:
    return DocumentControlService.from_deps(ctx.deps)


def _allowed_kb_refs(ctx: AuthContextDep) -> list[str]:
    snapshot = ctx.snapshot
    if snapshot.is_admin or snapshot.kb_scope == ResourceScope.ALL:
        return []
    if snapshot.kb_scope == ResourceScope.NONE:
        return []
    return sorted(snapshot.kb_names)


def _assert_can_view(ctx: AuthContextDep) -> None:
    snapshot = ctx.snapshot
    if snapshot.is_admin:
        return
    if snapshot.kb_scope == ResourceScope.NONE:
        raise HTTPException(status_code=403, detail="document_control_access_denied")
    if not (snapshot.can_review or snapshot.can_upload or snapshot.can_download or snapshot.can_view_kb_config):
        raise HTTPException(status_code=403, detail="document_control_access_denied")


def _assert_can_create(ctx: AuthContextDep, target_kb_id: str) -> None:
    if not ctx.snapshot.can_upload and not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="upload_forbidden")
    kb_info = resolve_kb_ref(ctx.deps, target_kb_id)
    assert_kb_allowed(ctx.snapshot, kb_info.variants or (target_kb_id,))


def _assert_can_submit(ctx: AuthContextDep, *kb_refs: str | None) -> None:
    if not ctx.snapshot.can_upload and not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="submit_forbidden")
    variants = tuple(str(item).strip() for item in kb_refs if str(item or "").strip())
    assert_kb_allowed(ctx.snapshot, variants)


def _assert_can_transition(ctx: AuthContextDep, *kb_refs: str | None) -> None:
    if not ctx.snapshot.can_review and not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="review_forbidden")
    variants = tuple(str(item).strip() for item in kb_refs if str(item or "").strip())
    assert_kb_allowed(ctx.snapshot, variants)


def _assert_admin(ctx: AuthContextDep) -> None:
    if not bool(getattr(ctx.snapshot, "is_admin", False)):
        raise HTTPException(status_code=403, detail="admin_required")


def _required_action_for_step(step_name: str | None) -> str:
    normalized = str(step_name or "").strip().lower()
    if normalized == "approve":
        return "approve"
    if normalized in {"cosign", "standardize_review"}:
        return "review"
    return "review"


def _assert_admin(ctx: AuthContextDep) -> None:
    if not bool(getattr(ctx.snapshot, "is_admin", False)):
        raise HTTPException(status_code=403, detail="admin_required")


@router.get("/quality-system/doc-control/documents")
def list_controlled_documents(
    ctx: AuthContextDep,
    doc_code: str | None = None,
    title: str | None = None,
    document_type: str | None = None,
    product_name: str | None = None,
    registration_ref: str | None = None,
    status: str | None = None,
    query: str | None = None,
    limit: int = 100,
):
    assert_capability(ctx, resource="document_control", action="review")
    _assert_can_view(ctx)
    items = _service(ctx).list_documents(
        allowed_kb_refs=_allowed_kb_refs(ctx),
        doc_code=doc_code,
        title=title,
        document_type=document_type,
        product_name=product_name,
        registration_ref=registration_ref,
        status=status,
        query=query,
        limit=limit,
    )
    return {"count": len(items), "items": [item.as_dict() for item in items]}


@router.get("/quality-system/doc-control/documents/{controlled_document_id}")
def get_controlled_document(controlled_document_id: str, ctx: AuthContextDep):
    assert_capability(ctx, resource="document_control", action="review")
    _assert_can_view(ctx)
    try:
        document = _service(ctx).get_document(controlled_document_id=controlled_document_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    refs = _allowed_kb_refs(ctx)
    if refs:
        allowed = set(refs)
        if document.target_kb_id not in allowed and (document.target_kb_name or "") not in allowed:
            raise HTTPException(status_code=403, detail="document_control_access_denied")
    return {"document": document.as_dict()}


@router.get("/quality-system/doc-control/workflows")
def list_document_control_workflows(ctx: AuthContextDep):
    _assert_admin(ctx)
    items = _service(ctx).list_document_type_workflows()
    return {"items": items, "count": len(items)}


@router.get("/quality-system/doc-control/workflows/{document_type}")
def get_document_control_workflow(document_type: str, ctx: AuthContextDep):
    _assert_admin(ctx)
    try:
        workflow = _service(ctx).get_document_type_workflow(document_type=document_type)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"workflow": workflow}


@router.put("/quality-system/doc-control/workflows/{document_type}")
def upsert_document_control_workflow(document_type: str, body: DocumentControlWorkflowRequest, ctx: AuthContextDep):
    _assert_admin(ctx)
    try:
        workflow = _service(ctx).upsert_document_type_workflow(
            document_type=document_type,
            name=body.name,
            steps=[item.model_dump() for item in body.steps],
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"workflow": workflow}


@router.get("/quality-system/doc-control/workflows")
def list_document_control_workflows(ctx: AuthContextDep):
    _assert_admin(ctx)
    items = _service(ctx).list_document_type_workflows()
    return {"items": items, "count": len(items)}


@router.get("/quality-system/doc-control/workflows/{document_type}")
def get_document_control_workflow(document_type: str, ctx: AuthContextDep):
    _assert_admin(ctx)
    try:
        workflow = _service(ctx).get_document_type_workflow(document_type=document_type)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"workflow": workflow}


@router.put("/quality-system/doc-control/workflows/{document_type}")
def upsert_document_control_workflow(document_type: str, body: DocumentControlWorkflowRequest, ctx: AuthContextDep):
    _assert_admin(ctx)
    try:
        workflow = _service(ctx).upsert_document_type_workflow(
            document_type=document_type,
            name=body.name,
            steps=[item.model_dump() for item in body.steps],
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"workflow": workflow}


@router.put("/quality-system/doc-control/documents/{controlled_document_id}/distribution-departments")
def set_controlled_document_distribution_departments(
    controlled_document_id: str,
    body: DistributionDepartmentsRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="review")
    _assert_can_view(ctx)
    try:
        document = _service(ctx).get_document(controlled_document_id=controlled_document_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    refs = _allowed_kb_refs(ctx)
    if refs:
        allowed = set(refs)
        if document.target_kb_id not in allowed and (document.target_kb_name or "") not in allowed:
            raise HTTPException(status_code=403, detail="document_control_access_denied")
    try:
        department_ids = _service(ctx).set_document_distribution_departments(
            controlled_document_id=controlled_document_id,
            department_ids=body.department_ids,
            ctx=ctx,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"controlled_document_id": controlled_document_id, "department_ids": department_ids}


@router.get("/quality-system/doc-control/documents/{controlled_document_id}/distribution-departments")
def get_controlled_document_distribution_departments(
    controlled_document_id: str,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="review")
    _assert_can_view(ctx)
    try:
        document = _service(ctx).get_document(controlled_document_id=controlled_document_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    refs = _allowed_kb_refs(ctx)
    if refs:
        allowed = set(refs)
        if document.target_kb_id not in allowed and (document.target_kb_name or "") not in allowed:
            raise HTTPException(status_code=403, detail="document_control_access_denied")
    try:
        department_ids = _service(ctx).get_document_distribution_departments(controlled_document_id=controlled_document_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"controlled_document_id": controlled_document_id, "department_ids": department_ids}


@router.post("/quality-system/doc-control/documents")
def create_controlled_document(
    ctx: AuthContextDep,
    doc_code: str = Form(...),
    title: str = Form(...),
    document_type: str = Form(...),
    target_kb_id: str = Form(...),
    product_name: str = Form(...),
    registration_ref: str = Form(...),
    change_summary: str | None = Form(None),
    file: UploadFile = File(...),
):
    assert_capability(ctx, resource="document_control", action="create")
    _assert_can_create(ctx, target_kb_id)
    try:
        document = _service(ctx).create_document(
            doc_code=doc_code,
            title=title,
            document_type=document_type,
            target_kb_id=target_kb_id,
            created_by=str(ctx.payload.sub),
            upload_file=file,
            product_name=product_name,
            registration_ref=registration_ref,
            change_summary=change_summary,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}


@router.post("/quality-system/doc-control/documents/{controlled_document_id}/revisions")
def create_controlled_revision(
    controlled_document_id: str,
    ctx: AuthContextDep,
    change_summary: str | None = Form(None),
    file: UploadFile = File(...),
):
    assert_capability(ctx, resource="document_control", action="create")
    try:
        current = _service(ctx).get_document(controlled_document_id=controlled_document_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_create(ctx, current.target_kb_id)
    try:
        document = _service(ctx).create_revision(
            controlled_document_id=controlled_document_id,
            created_by=str(ctx.payload.sub),
            upload_file=file,
            change_summary=change_summary,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/approval/submit")
def submit_controlled_revision_for_approval(
    controlled_revision_id: str,
    body: RevisionWorkflowActionRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="create")
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_submit(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        document = _service(ctx).submit_revision_for_approval(
            controlled_revision_id=controlled_revision_id,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/approval/approve")
def approve_controlled_revision_step(
    controlled_revision_id: str,
    body: RevisionWorkflowActionRequest,
    ctx: AuthContextDep,
):
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    assert_capability(ctx, resource="document_control", action=_required_action_for_step(revision.current_approval_step_name))
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        document = _service(ctx).approve_revision_approval_step(
            controlled_revision_id=controlled_revision_id,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/approval/reject")
def reject_controlled_revision_step(
    controlled_revision_id: str,
    body: RevisionWorkflowActionRequest,
    ctx: AuthContextDep,
):
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    assert_capability(ctx, resource="document_control", action=_required_action_for_step(revision.current_approval_step_name))
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        document = _service(ctx).reject_revision_approval_step(
            controlled_revision_id=controlled_revision_id,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/approval/add-sign")
def add_sign_controlled_revision_step(
    controlled_revision_id: str,
    body: RevisionAddSignRequest,
    ctx: AuthContextDep,
):
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    assert_capability(ctx, resource="document_control", action=_required_action_for_step(revision.current_approval_step_name))
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        document = _service(ctx).add_sign_revision_approval_step(
            controlled_revision_id=controlled_revision_id,
            approver_user_id=body.approver_user_id,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/approval/remind-overdue")
def remind_overdue_controlled_revision_step(
    controlled_revision_id: str,
    body: RevisionWorkflowActionRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="review")
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        result = _service(ctx).remind_overdue_revision_approval_step(
            controlled_revision_id=controlled_revision_id,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"result": result}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/approval/remind-overdue")
def remind_overdue_controlled_revision_step(
    controlled_revision_id: str,
    body: RevisionWorkflowActionRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="review")
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        result = _service(ctx).remind_overdue_revision_approval_step(
            controlled_revision_id=controlled_revision_id,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"result": result}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/publish")
def publish_controlled_revision(
    controlled_revision_id: str,
    body: RevisionPublishRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="publish")
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        document = _service(ctx).publish_revision(
            controlled_revision_id=controlled_revision_id,
            release_mode=body.release_mode,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/publish/manual-archive-complete")
def complete_manual_release_archive(
    controlled_revision_id: str,
    body: RevisionWorkflowActionRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="publish")
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        document = _service(ctx).complete_manual_release_archive(
            controlled_revision_id=controlled_revision_id,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}


@router.get("/quality-system/doc-control/revisions/{controlled_revision_id}/department-acks")
def list_revision_department_acks(controlled_revision_id: str, ctx: AuthContextDep):
    assert_capability(ctx, resource="document_control", action="review")
    _assert_can_view(ctx)
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    variants = tuple(
        str(item).strip()
        for item in (revision.kb_id, revision.kb_dataset_id, revision.kb_name)
        if str(item or "").strip()
    )
    assert_kb_allowed(ctx.snapshot, variants)
    try:
        items = _service(ctx).list_revision_department_acks(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"count": len(items), "items": items}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/department-acks/{department_id}/confirm")
def confirm_revision_department_ack(
    controlled_revision_id: str,
    department_id: int,
    body: DepartmentAckConfirmRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="review")
    _assert_can_view(ctx)
    try:
        ack = _service(ctx).confirm_revision_department_ack(
            controlled_revision_id=controlled_revision_id,
            department_id=department_id,
            ctx=ctx,
            notes=body.notes,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"ack": ack}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/department-acks/remind-overdue")
def remind_overdue_revision_department_acks(
    controlled_revision_id: str,
    body: RevisionWorkflowActionRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="publish")
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        result = _service(ctx).remind_overdue_revision_department_acks(
            controlled_revision_id=controlled_revision_id,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"result": result}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/obsolete/initiate")
def initiate_obsolete_controlled_revision(
    controlled_revision_id: str,
    body: ObsoleteInitiateRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="obsolete")
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        document = _service(ctx).initiate_revision_obsolete(
            controlled_revision_id=controlled_revision_id,
            ctx=ctx,
            retirement_reason=body.retirement_reason,
            retention_until_ms=body.retention_until_ms,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/obsolete/approve")
def approve_obsolete_controlled_revision(
    controlled_revision_id: str,
    body: RevisionWorkflowActionRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="obsolete")
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        document = _service(ctx).approve_revision_obsolete(
            controlled_revision_id=controlled_revision_id,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/obsolete/destruction/confirm")
def confirm_obsolete_destruction_controlled_revision(
    controlled_revision_id: str,
    body: DestructionConfirmRequest,
    ctx: AuthContextDep,
):
    assert_capability(ctx, resource="document_control", action="obsolete")
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        document = _service(ctx).confirm_revision_destruction(
            controlled_revision_id=controlled_revision_id,
            ctx=ctx,
            destruction_notes=body.destruction_notes,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}

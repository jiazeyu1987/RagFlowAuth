from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.core.training_support import resolve_training_compliance_service
from backend.services.training_compliance import TrainingComplianceError
from backend.services.users.store import UserStore

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


class TrainingAssignmentGenerateBody(BaseModel):
    controlled_revision_id: str
    assignee_user_ids: list[str] | None = None
    min_read_minutes: int = 15
    note: str | None = None


class AssignmentAcknowledgeBody(BaseModel):
    decision: str
    question_text: str | None = None


class QuestionResolveBody(BaseModel):
    resolution_text: str


def _service_from_ctx(ctx: AuthContextDep):
    return resolve_training_compliance_service(ctx.deps)


def _user_store_from_ctx(ctx: AuthContextDep):
    service = _service_from_ctx(ctx)
    db_path = getattr(service, "db_path", None)
    if db_path:
        return UserStore(db_path=str(db_path))
    return ctx.deps.user_store


def _ensure_user_exists(ctx: AuthContextDep, user_id: str, *, field_name: str):
    user = _user_store_from_ctx(ctx).get_by_user_id(str(user_id).strip())
    if user is None:
        raise HTTPException(status_code=400, detail=f"{field_name}_not_found")
    return user


def _wrap_payload(field: str, item: object) -> dict[str, object]:
    if not isinstance(item, dict):
        raise HTTPException(status_code=500, detail=f"{field}_invalid_payload")
    return {field: item}


def _capability_allowed(ctx: AuthContextDep, *, resource: str, action: str) -> bool:
    capabilities = ctx.snapshot.capabilities_dict()
    capability = capabilities.get(resource, {}).get(action, {})
    scope = str(capability.get("scope") or "none")
    return scope == "all" or (scope == "set" and bool(capability.get("targets")))


def _ensure_training_ack_capability(ctx: AuthContextDep, *, action: str) -> None:
    if _capability_allowed(ctx, resource="training_ack", action=action):
        return
    raise HTTPException(status_code=403, detail="training_ack_forbidden")


def _active_user_ids(ctx: AuthContextDep) -> list[str]:
    users = ctx.deps.user_store.list_users(status="active", limit=1000)
    return [str(item.user_id) for item in users if getattr(item, "user_id", None)]


def _notify_training_event(
    ctx: AuthContextDep,
    *,
    event_type: str,
    recipients: list[str],
    payload: dict,
) -> None:
    manager = getattr(ctx.deps, "notification_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="notification_manager_unavailable")
    dedupe_key = f"{event_type}:{payload.get('dedupe_ref') or payload.get('assignment_id') or payload.get('thread_id') or ''}"
    manager.notify_event(
        event_type=event_type,
        payload=payload,
        recipients=[{"user_id": uid} for uid in recipients if str(uid or "").strip()],
        dedupe_key=dedupe_key,
        allow_duplicate=False,
        channel_types=["in_app"],
        audit={
            "actor_user_id": str(ctx.user.user_id),
            "actor_username": str(getattr(ctx.user, "username", "") or ""),
        },
    )
    manager.dispatch_pending(limit=200)


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
    return _wrap_payload("requirement", item)


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
    return _wrap_payload("record", item)


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
    return _wrap_payload("certification", item)


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
        item = service.evaluate_action_status(
            user_id=str(user.user_id),
            role_code=str(getattr(user, "role", "") or ""),
            controlled_action=controlled_action,
        )
    except TrainingComplianceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    return _wrap_payload("status", item)


@router.get("/training-compliance/effective-revisions")
def list_effective_revisions(ctx: AuthContextDep, limit: int = 100):
    _ensure_training_ack_capability(ctx, action="assign")
    service = _service_from_ctx(ctx)
    items = service.list_effective_revisions(limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/training-compliance/assignments/generate")
def generate_training_assignments(body: TrainingAssignmentGenerateBody, ctx: AuthContextDep):
    _ensure_training_ack_capability(ctx, action="assign")
    service = _service_from_ctx(ctx)
    assignee_user_ids = body.assignee_user_ids or _active_user_ids(ctx)
    for assignee in assignee_user_ids:
        _ensure_user_exists(ctx, assignee, field_name="assignee_user_id")
    try:
        items = service.create_training_assignments(
            controlled_revision_id=body.controlled_revision_id,
            assigned_by_user_id=str(ctx.user.user_id),
            assignee_user_ids=assignee_user_ids,
            min_read_minutes=body.min_read_minutes,
            note=body.note,
        )
    except TrainingComplianceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    for item in items:
        _notify_training_event(
            ctx,
            event_type="training_assignment_created",
            recipients=[str(item["assignee_user_id"])],
            payload={
                "title": "培训任务待确认",
                "body": f"{item['doc_code']} v{item['revision_no']} 已生效，请完成培训确认。",
                "link_path": f"/quality-system/training?assignment_id={item['assignment_id']}",
                "assignment_id": item["assignment_id"],
                "controlled_revision_id": item["controlled_revision_id"],
                "dedupe_ref": item["assignment_id"],
            },
        )
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is not None:
        manager.safe_log_ctx_event(
            ctx=ctx,
            action="training_assignment_generate",
            source="training_compliance",
            resource_type="training_assignment_batch",
            resource_id=body.controlled_revision_id,
            event_type="create",
            meta={"count": len(items), "min_read_minutes": body.min_read_minutes},
        )
    return {"items": items, "count": len(items)}


@router.get("/training-compliance/assignments")
def list_my_training_assignments(ctx: AuthContextDep, status: str | None = None, limit: int = 100):
    service = _service_from_ctx(ctx)
    items = service.list_assignments(
        assignee_user_id=str(ctx.user.user_id),
        status=status,
        limit=limit,
    )
    return {"items": items, "count": len(items)}


@router.post("/training-compliance/assignments/{assignment_id}/acknowledge")
def acknowledge_training_assignment(assignment_id: str, body: AssignmentAcknowledgeBody, ctx: AuthContextDep):
    service = _service_from_ctx(ctx)
    try:
        item = service.acknowledge_assignment(
            assignment_id=assignment_id,
            assignee_user_id=str(ctx.user.user_id),
            decision=body.decision,
            question_text=body.question_text,
        )
    except TrainingComplianceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is not None:
        manager.safe_log_ctx_event(
            ctx=ctx,
            action="training_assignment_acknowledge",
            source="training_compliance",
            resource_type="training_assignment",
            resource_id=item["assignment_id"],
            event_type="update",
            meta={"decision": item["decision"], "status": item["status"]},
        )

    if item["decision"] == "questioned" and item.get("question_thread_id"):
        reviewers = [
            entry.user_id
            for entry in ctx.deps.user_store.list_users(status="active", limit=1000)
            if str(getattr(entry, "role", "") or "") in {"admin", "sub_admin"}
        ]
        _notify_training_event(
            ctx,
            event_type="training_assignment_questioned",
            recipients=[str(uid) for uid in reviewers],
            payload={
                "title": "培训疑问待处理",
                "body": f"{item['doc_code']} v{item['revision_no']} 收到疑问，请处理。",
                "link_path": f"/quality-system/training?thread_id={item['question_thread_id']}",
                "assignment_id": item["assignment_id"],
                "thread_id": item["question_thread_id"],
                "controlled_revision_id": item["controlled_revision_id"],
                "dedupe_ref": item["question_thread_id"],
            },
        )

    return {"assignment": item}


@router.get("/training-compliance/question-threads")
def list_question_threads(ctx: AuthContextDep, status: str | None = None, limit: int = 100):
    service = _service_from_ctx(ctx)
    can_review_questions = _capability_allowed(ctx, resource="training_ack", action="review_questions")
    assignee_user_id = None if can_review_questions else str(ctx.user.user_id)
    items = service.list_question_threads(status=status, assignee_user_id=assignee_user_id, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/training-compliance/question-threads/{thread_id}/resolve")
def resolve_question_thread(thread_id: str, body: QuestionResolveBody, ctx: AuthContextDep):
    _ensure_training_ack_capability(ctx, action="review_questions")
    service = _service_from_ctx(ctx)
    try:
        item = service.resolve_question_thread(
            thread_id=thread_id,
            resolver_user_id=str(ctx.user.user_id),
            resolution_text=body.resolution_text,
        )
    except TrainingComplianceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    _notify_training_event(
        ctx,
        event_type="training_question_resolved",
        recipients=[item["assignee_user_id"]],
        payload={
            "title": "培训疑问已回复",
            "body": "你的培训疑问已处理，请查看回复并完成记录。",
            "link_path": f"/quality-system/training?thread_id={item['thread_id']}",
            "thread_id": item["thread_id"],
            "assignment_id": item["assignment_id"],
            "controlled_revision_id": item["controlled_revision_id"],
            "dedupe_ref": item["thread_id"],
        },
    )
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is not None:
        manager.safe_log_ctx_event(
            ctx=ctx,
            action="training_question_resolve",
            source="training_compliance",
            resource_type="quality_question_thread",
            resource_id=item["thread_id"],
            event_type="update",
            meta={"status": item["status"]},
        )
    return {"thread": item}

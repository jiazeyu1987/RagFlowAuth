from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.signature_support import resolve_signature_service, signature_manifestation_payload
from backend.services.audit_helpers import log_quality_audit_event
from backend.services.batch_records import BatchRecordsService, BatchRecordsServiceError
from backend.services.electronic_signature import ElectronicSignatureError


router = APIRouter()


class BatchRecordTemplateCreateBody(BaseModel):
    template_code: str
    template_name: str
    steps: list[dict[str, Any]]
    meta: dict[str, Any] | None = None


class BatchRecordTemplateVersionCreateBody(BaseModel):
    template_name: str
    steps: list[dict[str, Any]]
    meta: dict[str, Any] | None = None


class BatchRecordExecutionCreateBody(BaseModel):
    template_id: str
    batch_no: str
    title: str | None = None


class BatchRecordStepWriteBody(BaseModel):
    step_key: str
    payload: dict[str, Any]


class BatchRecordSignatureBody(BaseModel):
    sign_token: str
    meaning: str
    reason: str


def _service(ctx: AuthContextDep) -> BatchRecordsService:
    service = getattr(ctx.deps, "batch_records_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="batch_records_service_unavailable")
    return service


def _capability_allowed(ctx: AuthContextDep, *, action: str) -> bool:
    capabilities = ctx.snapshot.capabilities_dict()
    capability = capabilities.get("batch_records", {}).get(action, {})
    scope = str(capability.get("scope") or "none")
    return scope == "all" or (scope == "set" and bool(capability.get("targets")))


def _ensure_any_batch_records_access(ctx: AuthContextDep) -> None:
    for action in ("template_manage", "execute", "sign", "review", "export"):
        if _capability_allowed(ctx, action=action):
            return
    raise HTTPException(status_code=403, detail="batch_records_forbidden")


def _ensure_batch_records_action(ctx: AuthContextDep, *, action: str) -> None:
    if _capability_allowed(ctx, action=action):
        return
    raise HTTPException(status_code=403, detail="batch_records_forbidden")


def _request_context_fields(request: Request) -> dict[str, Any]:
    return {
        "request_id": getattr(getattr(request, "state", None), "request_id", None),
        "client_ip": getattr(getattr(request, "client", None), "host", None),
    }


@router.get("/quality-system/batch-records/templates")
def list_batch_record_templates(
    ctx: AuthContextDep,
    include_versions: bool = False,
    include_obsolete: bool = False,
    limit: int = 100,
):
    _ensure_any_batch_records_access(ctx)
    try:
        items = _service(ctx).list_templates(
            include_versions=bool(include_versions),
            include_obsolete=bool(include_obsolete),
            limit=limit,
        )
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    return {"items": items, "count": len(items)}


@router.get("/quality-system/batch-records/templates/{template_id}")
def get_batch_record_template(template_id: str, ctx: AuthContextDep):
    _ensure_any_batch_records_access(ctx)
    try:
        template = _service(ctx).get_template(template_id=template_id)
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    return {"template": template}


@router.post("/quality-system/batch-records/templates")
def create_batch_record_template(body: BatchRecordTemplateCreateBody, ctx: AuthContextDep, request: Request):
    _ensure_batch_records_action(ctx, action="template_manage")
    try:
        template = _service(ctx).create_template(
            template_code=body.template_code,
            template_name=body.template_name,
            steps=body.steps,
            meta=body.meta,
            actor_user_id=str(ctx.user.user_id),
        )
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    log_quality_audit_event(
        deps=ctx.deps,
        ctx=ctx,
        action="batch_record_template_create",
        source="batch_records",
        resource_type="batch_record_template",
        resource_id=str(template["template_id"]),
        event_type="create",
        before=None,
        after=template,
        meta={"template_code": template["template_code"], "version_no": template["version_no"]},
        **_request_context_fields(request),
    )
    return {"template": template}


@router.post("/quality-system/batch-records/templates/{template_code}/versions")
def create_batch_record_template_version(
    template_code: str,
    body: BatchRecordTemplateVersionCreateBody,
    ctx: AuthContextDep,
    request: Request,
):
    _ensure_batch_records_action(ctx, action="template_manage")
    try:
        template = _service(ctx).create_template_version(
            template_code=template_code,
            template_name=body.template_name,
            steps=body.steps,
            meta=body.meta,
            actor_user_id=str(ctx.user.user_id),
        )
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    log_quality_audit_event(
        deps=ctx.deps,
        ctx=ctx,
        action="batch_record_template_version_create",
        source="batch_records",
        resource_type="batch_record_template",
        resource_id=str(template["template_id"]),
        event_type="create",
        before=None,
        after=template,
        meta={"template_code": template["template_code"], "version_no": template["version_no"]},
        **_request_context_fields(request),
    )
    return {"template": template}


@router.post("/quality-system/batch-records/templates/{template_id}/publish")
def publish_batch_record_template(template_id: str, ctx: AuthContextDep, request: Request):
    _ensure_batch_records_action(ctx, action="template_manage")
    try:
        before = _service(ctx).get_template(template_id=template_id)
        template = _service(ctx).publish_template(template_id=template_id, actor_user_id=str(ctx.user.user_id))
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    log_quality_audit_event(
        deps=ctx.deps,
        ctx=ctx,
        action="batch_record_template_publish",
        source="batch_records",
        resource_type="batch_record_template",
        resource_id=str(template["template_id"]),
        event_type="update",
        before=before,
        after=template,
        meta={"template_code": template["template_code"], "version_no": template["version_no"]},
        **_request_context_fields(request),
    )
    return {"template": template}


@router.get("/quality-system/batch-records/executions")
def list_batch_record_executions(
    ctx: AuthContextDep,
    status: str | None = None,
    template_code: str | None = None,
    batch_no: str | None = None,
    limit: int = 100,
):
    _ensure_any_batch_records_access(ctx)
    try:
        items = _service(ctx).list_executions(
            status=status,
            template_code=template_code,
            batch_no=batch_no,
            limit=limit,
        )
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    return {"items": items, "count": len(items)}


@router.post("/quality-system/batch-records/executions")
def create_batch_record_execution(body: BatchRecordExecutionCreateBody, ctx: AuthContextDep, request: Request):
    _ensure_batch_records_action(ctx, action="execute")
    try:
        bundle = _service(ctx).create_execution(
            template_id=body.template_id,
            batch_no=body.batch_no,
            title=body.title,
            actor_user_id=str(ctx.user.user_id),
        )
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    execution = bundle.get("execution") or {}
    log_quality_audit_event(
        deps=ctx.deps,
        ctx=ctx,
        action="batch_record_execution_create",
        source="batch_records",
        resource_type="batch_record_execution",
        resource_id=str(execution.get("execution_id") or ""),
        event_type="create",
        before=None,
        after=execution,
        meta={"template_id": execution.get("template_id"), "batch_no": execution.get("batch_no")},
        **_request_context_fields(request),
    )
    return {"bundle": bundle}


def _resolve_signatures(ctx: AuthContextDep, execution: dict[str, Any]) -> dict[str, Any]:
    signature_service = resolve_signature_service(ctx.deps)
    signed_signature_id = execution.get("signed_signature_id")
    reviewed_signature_id = execution.get("reviewed_signature_id")

    signed_signature = None
    reviewed_signature = None

    if signed_signature_id:
        signature = signature_service.get_signature(str(signed_signature_id))
        signed_signature = signature_manifestation_payload(
            signature,
            verified=bool(signature_service.verify_signature(signature_id=str(signature.signature_id))),
        )

    if reviewed_signature_id:
        signature = signature_service.get_signature(str(reviewed_signature_id))
        reviewed_signature = signature_manifestation_payload(
            signature,
            verified=bool(signature_service.verify_signature(signature_id=str(signature.signature_id))),
        )

    return {
        "signed_signature": signed_signature,
        "reviewed_signature": reviewed_signature,
    }


@router.get("/quality-system/batch-records/executions/{execution_id}")
def get_batch_record_execution(execution_id: str, ctx: AuthContextDep):
    _ensure_any_batch_records_access(ctx)
    try:
        bundle = _service(ctx).get_execution(execution_id=execution_id)
        execution = bundle.get("execution") or {}
        signatures = _resolve_signatures(ctx, execution)
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    except ElectronicSignatureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    return {
        "bundle": bundle,
        **signatures,
    }


@router.post("/quality-system/batch-records/executions/{execution_id}/steps")
def write_batch_record_step(execution_id: str, body: BatchRecordStepWriteBody, ctx: AuthContextDep, request: Request):
    _ensure_batch_records_action(ctx, action="execute")
    try:
        entry = _service(ctx).write_step_entry(
            execution_id=execution_id,
            step_key=body.step_key,
            payload=body.payload,
            actor_user_id=str(ctx.user.user_id),
            actor_username=str(getattr(ctx.user, "username", "") or ""),
        )
        bundle = _service(ctx).get_execution(execution_id=execution_id)
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    log_quality_audit_event(
        deps=ctx.deps,
        ctx=ctx,
        action="batch_record_step_write",
        source="batch_records",
        resource_type="batch_record_execution",
        resource_id=str(execution_id),
        event_type="update",
        before=None,
        after=entry,
        meta={"step_key": body.step_key, "entry_id": entry.get("entry_id")},
        **_request_context_fields(request),
    )
    return {"bundle": bundle, "entry": entry}


def _require_exportable_status(execution: dict[str, Any]) -> None:
    status = str(execution.get("status") or "")
    if status in {"signed", "reviewed"}:
        return
    raise HTTPException(status_code=409, detail="batch_record_execution_not_ready_for_export")


@router.post("/quality-system/batch-records/executions/{execution_id}/sign")
def sign_batch_record_execution(
    execution_id: str,
    body: BatchRecordSignatureBody,
    ctx: AuthContextDep,
    request: Request,
):
    _ensure_batch_records_action(ctx, action="sign")
    service = _service(ctx)
    signature_service = resolve_signature_service(ctx.deps)
    try:
        before_bundle = service.get_execution(execution_id=execution_id)
        record_payload = service.build_execution_record_payload(execution_id=execution_id)
        signing_context = signature_service.consume_sign_token(
            user=ctx.user,
            sign_token=body.sign_token,
            action="batch_record_execution_sign",
        )
        signature = signature_service.create_signature(
            signing_context=signing_context,
            user=ctx.user,
            record_type="batch_record_execution",
            record_id=str(execution_id),
            action="batch_record_execution_sign",
            meaning=body.meaning,
            reason=body.reason,
            record_payload=record_payload,
        )
        bundle = service.set_execution_signed(
            execution_id=execution_id,
            signature_id=str(signature.signature_id),
            actor_user_id=str(ctx.user.user_id),
        )
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    except ElectronicSignatureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    after_execution = (bundle.get("execution") or {})
    before_execution = (before_bundle.get("execution") or {})
    log_quality_audit_event(
        deps=ctx.deps,
        ctx=ctx,
        action="batch_record_execution_sign",
        source="batch_records",
        resource_type="batch_record_execution",
        resource_id=str(execution_id),
        event_type="update",
        before={
            "status": before_execution.get("status"),
            "signed_signature_id": before_execution.get("signed_signature_id"),
        },
        after={
            "status": after_execution.get("status"),
            "signed_signature_id": after_execution.get("signed_signature_id"),
        },
        reason=body.reason,
        signature_id=str(signature.signature_id),
        meta={"signature_meaning": body.meaning},
        **_request_context_fields(request),
    )
    return {
        "bundle": bundle,
        "signature": signature_manifestation_payload(
            signature,
            verified=bool(signature_service.verify_signature(signature_id=str(signature.signature_id))),
        ),
    }


@router.post("/quality-system/batch-records/executions/{execution_id}/review")
def review_batch_record_execution(
    execution_id: str,
    body: BatchRecordSignatureBody,
    ctx: AuthContextDep,
    request: Request,
):
    _ensure_batch_records_action(ctx, action="review")
    service = _service(ctx)
    signature_service = resolve_signature_service(ctx.deps)
    try:
        before_bundle = service.get_execution(execution_id=execution_id)
        record_payload = service.build_execution_record_payload(execution_id=execution_id)
        signing_context = signature_service.consume_sign_token(
            user=ctx.user,
            sign_token=body.sign_token,
            action="batch_record_execution_review",
        )
        signature = signature_service.create_signature(
            signing_context=signing_context,
            user=ctx.user,
            record_type="batch_record_execution",
            record_id=str(execution_id),
            action="batch_record_execution_review",
            meaning=body.meaning,
            reason=body.reason,
            record_payload=record_payload,
        )
        bundle = service.set_execution_reviewed(
            execution_id=execution_id,
            signature_id=str(signature.signature_id),
            actor_user_id=str(ctx.user.user_id),
        )
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    except ElectronicSignatureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    after_execution = (bundle.get("execution") or {})
    before_execution = (before_bundle.get("execution") or {})
    log_quality_audit_event(
        deps=ctx.deps,
        ctx=ctx,
        action="batch_record_execution_review",
        source="batch_records",
        resource_type="batch_record_execution",
        resource_id=str(execution_id),
        event_type="update",
        before={
            "status": before_execution.get("status"),
            "reviewed_signature_id": before_execution.get("reviewed_signature_id"),
        },
        after={
            "status": after_execution.get("status"),
            "reviewed_signature_id": after_execution.get("reviewed_signature_id"),
        },
        reason=body.reason,
        signature_id=str(signature.signature_id),
        meta={"signature_meaning": body.meaning},
        **_request_context_fields(request),
    )
    return {
        "bundle": bundle,
        "signature": signature_manifestation_payload(
            signature,
            verified=bool(signature_service.verify_signature(signature_id=str(signature.signature_id))),
        ),
    }


@router.post("/quality-system/batch-records/executions/{execution_id}/export")
def export_batch_record_execution(execution_id: str, ctx: AuthContextDep, request: Request):
    _ensure_batch_records_action(ctx, action="export")
    service = _service(ctx)
    try:
        bundle = service.get_execution(execution_id=execution_id)
        execution = bundle.get("execution") or {}
        _require_exportable_status(execution)
        export_payload = service.build_execution_record_payload(execution_id=execution_id)
        signatures = _resolve_signatures(ctx, execution)
    except BatchRecordsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    except ElectronicSignatureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    log_quality_audit_event(
        deps=ctx.deps,
        ctx=ctx,
        action="batch_record_execution_export",
        source="batch_records",
        resource_type="batch_record_execution",
        resource_id=str(execution_id),
        event_type="export",
        before=None,
        after=None,
        meta={"status": execution.get("status")},
        **_request_context_fields(request),
    )

    filename = f"batch-record-{execution_id}.json"
    return {
        "filename": filename,
        "export": {
            **export_payload,
            **signatures,
        },
    }


from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import (
    assert_can_upload,
    assert_kb_allowed,
)
from backend.models.operation_approval import OperationApprovalRequestBrief
from backend.services.audit_helpers import actor_fields_from_ctx


router = APIRouter()


def _get_allowed_extensions_payload(ctx: AuthContextDep) -> dict:
    settings_obj = ctx.deps.upload_settings_store.get()
    return {
        "allowed_extensions": settings_obj.allowed_extensions,
        "updated_at_ms": settings_obj.updated_at_ms,
    }


@router.get("/settings/allowed-extensions")
def get_allowed_extensions(ctx: AuthContextDep):
    return _get_allowed_extensions_payload(ctx)


@router.put("/settings/allowed-extensions")
def update_allowed_extensions(request: Request, ctx: AuthContextDep, body: dict):
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")
    extensions = body.get("allowed_extensions")
    change_reason = str((body or {}).get("change_reason") or "").strip()
    if not change_reason:
        raise HTTPException(status_code=400, detail="change_reason_required")
    before = ctx.deps.upload_settings_store.get()
    try:
        updated = ctx.deps.upload_settings_store.update_allowed_extensions(
            extensions,
            changed_by=ctx.payload.sub,
            change_reason=change_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    client_ip = getattr(getattr(request, "client", None), "host", None)
    ctx.deps.audit_log_manager.log_event(
        action="upload_settings_update",
        actor=ctx.payload.sub,
        source="knowledge",
        resource_type="upload_settings",
        resource_id="allowed_extensions",
        event_type="update",
        before={"allowed_extensions": before.allowed_extensions, "updated_at_ms": before.updated_at_ms},
        after={"allowed_extensions": updated.allowed_extensions, "updated_at_ms": updated.updated_at_ms},
        reason=change_reason,
        request_id=request_id,
        client_ip=client_ip,
        meta={"changed_keys": ["allowed_extensions"]},
        **actor_fields_from_ctx(ctx.deps, ctx),
    )
    return {
        "allowed_extensions": updated.allowed_extensions,
        "updated_at_ms": updated.updated_at_ms,
    }


@router.post("/upload", response_model=OperationApprovalRequestBrief, status_code=202)
async def upload_document(
    request: Request,
    ctx: AuthContextDep,
    file: UploadFile = File(...),
):
    kb_ref = request.query_params.get("kb_id", "灞曞巺")
    snapshot = ctx.snapshot
    assert_can_upload(snapshot)
    assert_kb_allowed(snapshot, kb_ref)
    service = getattr(ctx.deps, "operation_approval_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="operation_approval_service_unavailable")
    try:
        brief = await service.create_request(
            operation_type="knowledge_file_upload",
            ctx=ctx,
            upload_file=file,
            kb_ref=kb_ref,
        )
    except Exception as e:
        detail = getattr(e, "code", None) or str(e) or "operation_approval_create_failed"
        status_code = getattr(e, "status_code", 400)
        raise HTTPException(status_code=status_code, detail=detail) from e
    return OperationApprovalRequestBrief(**brief)

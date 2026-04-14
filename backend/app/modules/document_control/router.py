from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep, assert_capability
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import ResourceScope, assert_kb_allowed
from backend.services.document_control import DocumentControlError, DocumentControlService


router = APIRouter()


class RevisionTransitionRequest(BaseModel):
    target_status: str
    note: str | None = None


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


def _assert_can_transition(ctx: AuthContextDep, *kb_refs: str | None) -> None:
    if not ctx.snapshot.can_review and not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="review_forbidden")
    variants = tuple(str(item).strip() for item in kb_refs if str(item or "").strip())
    assert_kb_allowed(ctx.snapshot, variants)


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


@router.post("/quality-system/doc-control/revisions/{controlled_revision_id}/transitions")
def transition_controlled_revision(
    controlled_revision_id: str,
    body: RevisionTransitionRequest,
    ctx: AuthContextDep,
):
    required_action = {
        "in_review": "review",
        "approved": "approve",
        "effective": "effective",
        "obsolete": "obsolete",
    }.get(str(body.target_status or "").strip(), "review")
    assert_capability(ctx, resource="document_control", action=required_action)
    try:
        revision = _service(ctx).get_revision(controlled_revision_id=controlled_revision_id)
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _assert_can_transition(ctx, revision.kb_id, revision.kb_dataset_id, revision.kb_name)
    try:
        document = _service(ctx).transition_revision(
            controlled_revision_id=controlled_revision_id,
            target_status=body.target_status,
            ctx=ctx,
            note=body.note,
        )
    except DocumentControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"document": document.as_dict()}

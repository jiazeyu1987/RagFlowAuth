from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import ResourceScope, assert_can_review, assert_kb_allowed
from backend.services.audit_helpers import actor_fields_from_ctx
from backend.app.core.user_display import resolve_user_display_names
from backend.services.compliance import RetiredRecordsService
from backend.services.documents.document_manager import DocumentManager


router = APIRouter()


def _request_audit_fields(request: Request) -> tuple[str | None, str | None]:
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    client_ip = getattr(getattr(request, "client", None), "host", None)
    return request_id, client_ip


def _retired_payload(doc, usernames: dict[str, str]) -> dict:
    return {
        "doc_id": doc.doc_id,
        "filename": doc.filename,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "uploaded_by": doc.uploaded_by,
        "uploaded_by_name": usernames.get(doc.uploaded_by) if doc.uploaded_by else None,
        "reviewed_by": doc.reviewed_by,
        "reviewed_by_name": usernames.get(doc.reviewed_by) if doc.reviewed_by else None,
        "status": doc.status,
        "kb_id": (doc.kb_name or doc.kb_id),
        "kb_dataset_id": getattr(doc, "kb_dataset_id", None),
        "logical_doc_id": getattr(doc, "logical_doc_id", None),
        "version_no": getattr(doc, "version_no", 1),
        "effective_status": getattr(doc, "effective_status", None),
        "archived_at_ms": getattr(doc, "archived_at_ms", None),
        "retention_until_ms": getattr(doc, "retention_until_ms", None),
        "retired_by": getattr(doc, "retired_by", None),
        "retired_by_name": usernames.get(getattr(doc, "retired_by", None)) if getattr(doc, "retired_by", None) else None,
        "retirement_reason": getattr(doc, "retirement_reason", None),
        "archive_manifest_path": getattr(doc, "archive_manifest_path", None),
        "archive_package_path": getattr(doc, "archive_package_path", None),
        "archive_package_sha256": getattr(doc, "archive_package_sha256", None),
        "file_sha256": getattr(doc, "file_sha256", None),
    }


@router.post("/documents/{doc_id}/retire")
def retire_document(
    doc_id: str,
    request: Request,
    body: dict | None,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document_not_found")
    assert_kb_allowed(snapshot, doc.kb_id)

    data = body or {}
    reason = str(data.get("retirement_reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="retirement_reason_required")
    try:
        retention_until_ms = int(data.get("retention_until_ms"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_retention_until_ms") from exc

    service = RetiredRecordsService(kb_store=deps.kb_store)
    try:
        retired = service.retire_document(
            doc_id=doc_id,
            retired_by=str(ctx.payload.sub),
            retired_by_username=getattr(ctx.user, "username", None),
            retirement_reason=reason,
            retention_until_ms=retention_until_ms,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    request_id, client_ip = _request_audit_fields(request)
    deps.audit_log_manager.log_event(
        action="document_retire",
        actor=ctx.payload.sub,
        source="knowledge_retired",
        resource_type="retired_document",
        resource_id=retired.doc_id,
        event_type="update",
        before={
            "doc_id": doc.doc_id,
            "effective_status": getattr(doc, "effective_status", None),
            "is_current": getattr(doc, "is_current", None),
            "archived_at_ms": getattr(doc, "archived_at_ms", None),
            "retention_until_ms": getattr(doc, "retention_until_ms", None),
        },
        after=_retired_payload(retired, {}),
        reason=reason,
        request_id=request_id,
        client_ip=client_ip,
        doc_id=retired.doc_id,
        filename=retired.filename,
        kb_id=(retired.kb_name or retired.kb_id),
        kb_dataset_id=getattr(retired, "kb_dataset_id", None),
        kb_name=getattr(retired, "kb_name", None) or (retired.kb_name or retired.kb_id),
        meta={
            "retention_until_ms": getattr(retired, "retention_until_ms", None),
            "archive_package_path": getattr(retired, "archive_package_path", None),
            "archive_package_sha256": getattr(retired, "archive_package_sha256", None),
        },
        **actor_fields_from_ctx(deps, ctx),
    )

    usernames = {}
    try:
        usernames = resolve_user_display_names(deps, {retired.uploaded_by, retired.reviewed_by, retired.retired_by} - {None, ""})
    except Exception:
        usernames = {}
    return _retired_payload(retired, usernames)


@router.get("/retired-documents")
def list_retired_documents(
    ctx: AuthContextDep,
    kb_id: str | None = None,
    limit: int = 100,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    DocumentManager(deps).assert_can_preview_knowledge(snapshot)
    service = RetiredRecordsService(kb_store=deps.kb_store)

    if snapshot.kb_scope == ResourceScope.NONE:
        docs = []
    elif kb_id:
        assert_kb_allowed(snapshot, kb_id)
        kb_info = resolve_kb_ref(deps, kb_id)
        docs = service.list_retired_documents(kb_refs=list(kb_info.variants), limit=limit)
    else:
        docs = service.list_retired_documents(limit=limit)
        if snapshot.kb_scope != ResourceScope.ALL:
            docs = [
                item
                for item in docs
                if (item.kb_id in snapshot.kb_names)
                or (item.kb_dataset_id is not None and item.kb_dataset_id in snapshot.kb_names)
                or (item.kb_name is not None and item.kb_name in snapshot.kb_names)
            ]

    user_ids = {item.uploaded_by for item in docs if item.uploaded_by}
    user_ids.update({item.reviewed_by for item in docs if item.reviewed_by})
    user_ids.update({getattr(item, "retired_by", None) for item in docs if getattr(item, "retired_by", None)})
    try:
        usernames = resolve_user_display_names(deps, user_ids)
    except Exception:
        usernames = {}
    return {"items": [_retired_payload(item, usernames) for item in docs], "count": len(docs)}


@router.get("/retired-documents/{doc_id}/download")
def download_retired_document(doc_id: str, ctx: AuthContextDep):
    mgr = DocumentManager(ctx.deps)
    return mgr.download_retired_knowledge_response(doc_id=doc_id, ctx=ctx)


@router.get("/retired-documents/{doc_id}/preview")
def preview_retired_document(
    request: Request,
    doc_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    DocumentManager(deps).assert_can_preview_knowledge(snapshot)

    service = RetiredRecordsService(kb_store=deps.kb_store)
    try:
        doc = service.get_retired_document(doc_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "document_retention_expired":
            raise HTTPException(status_code=410, detail=detail) from exc
        raise HTTPException(status_code=409, detail=detail) from exc

    assert_kb_allowed(snapshot, doc.kb_id)
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="file_not_found")

    ext = Path(doc.filename).suffix.lower()
    render = (request.query_params.get("render") or "").strip().lower()
    media_type = doc.mime_type
    if ext in {".txt", ".ini", ".log"}:
        media_type = "text/plain; charset=utf-8"
    elif ext in {".md", ".markdown"}:
        media_type = "text/markdown; charset=utf-8"
    elif ext in {".doc", ".docx", ".xlsx", ".xls"} and render == "html":
        try:
            from backend.app.core.paths import resolve_repo_path
            from backend.services.office_to_html import convert_office_path_to_html_bytes

            previews_dir = resolve_repo_path("data/previews")
            previews_dir.mkdir(parents=True, exist_ok=True)
            cached_html = previews_dir / f"retired_{doc_id}.html"
            html_bytes = convert_office_path_to_html_bytes(doc.file_path)
            cached_html.write_bytes(html_bytes)
            quoted = quote(f"{Path(doc.filename).stem}.html")
            return FileResponse(
                path=str(cached_html),
                media_type="text/html; charset=utf-8",
                headers={"Content-Disposition": f"inline; filename*=UTF-8''{quoted}"},
            )
        except Exception as exc:
            raise HTTPException(status_code=415, detail=f"office_preview_unavailable:{exc}") from exc

    quoted = quote(doc.filename)
    return FileResponse(
        path=doc.file_path,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quoted}"},
    )

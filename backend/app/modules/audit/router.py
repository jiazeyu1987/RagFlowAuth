from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.core.user_display import resolve_user_display_names
from backend.services.audit import AuditEvidenceExportService
from backend.services.compliance import ComplianceReviewPackageService, RetiredRecordsService

router = APIRouter()


def _require_audit_log_manager(ctx: AuthContextDep):
    manager = getattr(ctx.deps, "audit_log_manager", None)
    if manager is None or not hasattr(manager, "list_events") or not hasattr(manager, "log_ctx_event"):
        raise HTTPException(status_code=500, detail="audit_log_manager_unavailable")
    return manager


@router.get("/audit/events")
async def list_audit_events(
    ctx: AuthContextDep,
    _: AdminOnly,
    action: str | None = None,
    actor: str | None = None,
    username: str | None = None,
    company_id: int | None = None,
    department_id: int | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    event_type: str | None = None,
    signature_id: str | None = None,
    request_id: str | None = None,
    source: str | None = None,
    doc_id: str | None = None,
    filename: str | None = None,
    kb_id: str | None = None,
    kb_dataset_id: str | None = None,
    kb_name: str | None = None,
    kb_ref: str | None = None,
    from_ms: int | None = None,
    to_ms: int | None = None,
    offset: int = 0,
    limit: int = 200,
):
    """
    Unified audit events list (admin only).

    Covers:
    - auth_login/auth_logout
    - document_preview/document_upload/document_download/document_delete
    """
    manager = _require_audit_log_manager(ctx)
    result = manager.list_events(
        action=action,
        actor=actor,
        actor_username=username,
        company_id=company_id,
        department_id=department_id,
        resource_type=resource_type,
        resource_id=resource_id,
        event_type=event_type,
        signature_id=signature_id,
        request_id=request_id,
        source=source,
        doc_id=doc_id,
        filename=filename,
        kb_id=kb_id,
        kb_dataset_id=kb_dataset_id,
        kb_name=kb_name,
        kb_ref=kb_ref,
        from_ms=from_ms,
        to_ms=to_ms,
        offset=offset,
        limit=limit,
    )
    items = list(result.get("items") or [])
    names = resolve_user_display_names(ctx.deps, {str(item.get("actor") or "").strip() for item in items if item.get("actor")})
    for item in items:
        actor_id = str(item.get("actor") or "").strip()
        if actor_id and names.get(actor_id):
            item["full_name"] = names.get(actor_id)
    result["items"] = items
    return result

def _resolve_evidence_export_service(ctx: AuthContextDep) -> AuditEvidenceExportService:
    store = getattr(ctx.deps, "audit_log_store", None)
    db_path = getattr(store, "db_path", None)
    if not db_path:
        raise HTTPException(status_code=500, detail="audit_evidence_export_unavailable")
    return AuditEvidenceExportService(db_path=str(db_path))


def _resolve_review_package_service(request: Request) -> ComplianceReviewPackageService:
    repo_root = getattr(getattr(request, "app", None), "state", None)
    override_root = getattr(repo_root, "compliance_repo_root", None) if repo_root is not None else None
    return ComplianceReviewPackageService(repo_root=override_root)


def _resolve_retired_records_service(ctx: AuthContextDep) -> RetiredRecordsService:
    kb_store = getattr(ctx.deps, "kb_store", None)
    if kb_store is None:
        raise HTTPException(status_code=500, detail="retired_records_unavailable")
    return RetiredRecordsService(kb_store=kb_store)


@router.get("/audit/evidence-export")
async def export_audit_evidence(
    ctx: AuthContextDep,
    _: AdminOnly,
    from_ms: int | None = None,
    to_ms: int | None = None,
    action: str | None = None,
    doc_id: str | None = None,
    actor: str | None = None,
    signature_id: str | None = None,
    request_id: str | None = None,
    event_type: str | None = None,
    filename: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    source: str | None = None,
):
    service = _resolve_evidence_export_service(ctx)
    result = service.export_package(
        exported_by=str(ctx.payload.sub),
        exported_by_username=getattr(ctx.user, "username", None),
        filters={
            "from_ms": from_ms,
            "to_ms": to_ms,
            "action": action,
            "doc_id": doc_id,
            "actor": actor,
            "signature_id": signature_id,
            "request_id": request_id,
            "event_type": event_type,
            "filename": filename,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "source": source,
        },
    )
    manager = _require_audit_log_manager(ctx)
    manager.log_ctx_event(
        ctx=ctx,
        action="audit_evidence_export",
        source="audit",
        resource_type="inspection_evidence_package",
        resource_id=result.package_filename,
        event_type="export",
        meta={
            "package_filename": result.package_filename,
            "package_sha256": result.package_sha256,
            "counts": result.counts,
            "filters": result.manifest.get("metadata", {}).get("filters", {}),
        },
    )
    return Response(
        content=result.package_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{result.package_filename}"',
            "X-Evidence-Package-Sha256": result.package_sha256,
        },
    )


@router.get("/audit/controlled-documents")
async def list_controlled_documents(request: Request, ctx: AuthContextDep, _: AdminOnly):
    service = _resolve_review_package_service(request)
    try:
        items = [item.as_dict() for item in service.list_controlled_documents()]
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "release_version": service.release_version,
        "company_id": getattr(ctx.user, "company_id", None),
        "count": len(items),
        "items": items,
    }


@router.get("/audit/review-package")
async def export_review_package(
    request: Request,
    ctx: AuthContextDep,
    _: AdminOnly,
    company_id: int | None = None,
):
    service = _resolve_review_package_service(request)
    try:
        result = service.export_review_package(
            exported_by=str(ctx.payload.sub),
            exported_by_username=getattr(ctx.user, "username", None),
            company_id=(int(company_id) if company_id is not None else getattr(ctx.user, "company_id", None)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    manager = _require_audit_log_manager(ctx)
    manager.log_ctx_event(
        ctx=ctx,
        action="compliance_review_package_export",
        source="audit",
        resource_type="controlled_document_review_package",
        resource_id=result.package_filename,
        event_type="export",
        meta={
            "package_filename": result.package_filename,
            "package_sha256": result.package_sha256,
            "release_version": result.manifest.get("metadata", {}).get("release_version"),
            "company_id": result.manifest.get("metadata", {}).get("company_id"),
            "document_count": len(result.manifest.get("documents") or []),
        },
    )
    return Response(
        content=result.package_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{result.package_filename}"',
            "X-Review-Package-Sha256": result.package_sha256,
        },
    )


@router.get("/audit/retired-records")
async def list_retired_records(
    ctx: AuthContextDep,
    _: AdminOnly,
    kb_id: str | None = None,
    limit: int = 100,
    include_expired: bool = False,
):
    service = _resolve_retired_records_service(ctx)
    items = service.list_retired_documents(
        kb_id=kb_id,
        limit=limit,
        include_expired=include_expired,
    )
    return {
        "count": len(items),
        "items": [
            {
                "doc_id": item.doc_id,
                "filename": item.filename,
                "kb_id": item.kb_id,
                "kb_dataset_id": item.kb_dataset_id,
                "kb_name": item.kb_name,
                "logical_doc_id": item.logical_doc_id,
                "version_no": item.version_no,
                "archived_at_ms": item.archived_at_ms,
                "retention_until_ms": item.retention_until_ms,
                "retired_by": item.retired_by,
                "retirement_reason": item.retirement_reason,
                "archive_manifest_path": item.archive_manifest_path,
                "archive_package_path": item.archive_package_path,
                "archive_package_sha256": item.archive_package_sha256,
                "file_sha256": item.file_sha256,
            }
            for item in items
        ],
    }


@router.get("/audit/retired-records/{doc_id}/package")
async def export_retired_record_package(
    ctx: AuthContextDep,
    _: AdminOnly,
    doc_id: str,
    allow_expired: bool = False,
):
    service = _resolve_retired_records_service(ctx)
    try:
        result = service.export_retired_record_package(doc_id=doc_id, allow_expired=allow_expired)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "document_retention_expired":
            raise HTTPException(status_code=410, detail=detail) from exc
        raise HTTPException(status_code=409, detail=detail) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    manager = _require_audit_log_manager(ctx)
    manager.log_ctx_event(
        ctx=ctx,
        action="retired_record_package_export",
        source="audit",
        resource_type="retired_record_package",
        resource_id=result.package_filename,
        event_type="export",
        meta={
            "doc_id": doc_id,
            "package_filename": result.package_filename,
            "package_sha256": result.package_sha256,
            "archived_at_ms": result.retired_document.get("archived_at_ms"),
            "retention_until_ms": result.retired_document.get("retention_until_ms"),
        },
    )
    return Response(
        content=result.package_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{result.package_filename}"',
            "X-Retired-Record-Package-Sha256": result.package_sha256,
        },
    )

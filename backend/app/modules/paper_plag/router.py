from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.app.core.authz import AuthContextDep
from backend.services.paper_plag_store import PaperPlagStore
from backend.services.paper_plagiarism_service import PaperPlagiarismService
from backend.services.system_feature_flag_store import FLAG_PAPER_PLAG_ENABLED, SystemFeatureFlagStore
from backend.services.unified_task_quota_service import UnifiedTaskQuotaService

router = APIRouter()


class PaperPlagSourceInput(BaseModel):
    source_doc_id: str | None = None
    source_title: str | None = None
    source_uri: str | None = None
    content_text: str = ""


class PaperPlagStartRequest(BaseModel):
    paper_id: str = Field(..., min_length=1)
    title: str = ""
    content_text: str = Field(..., min_length=1)
    note: str | None = None
    similarity_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    priority: int | None = Field(default=None, ge=1, le=1000)
    sources: list[PaperPlagSourceInput] = Field(default_factory=list)


class PaperVersionSaveRequest(BaseModel):
    title: str = ""
    content_text: str = Field(..., min_length=1)
    note: str | None = None


class PaperVersionDiffRequest(BaseModel):
    from_version_id: int = Field(..., ge=1)
    to_version_id: int = Field(..., ge=1)


class PaperVersionRollbackRequest(BaseModel):
    note: str | None = None


def _resolve_store(deps) -> PaperPlagStore:
    existing = getattr(deps, "paper_plag_store", None)
    if existing is not None:
        return existing
    kb_store = getattr(deps, "kb_store", None)
    db_path = str(getattr(kb_store, "db_path", "") or "")
    store = PaperPlagStore(db_path=db_path or None)
    try:
        setattr(deps, "paper_plag_store", store)
    except Exception:
        pass
    return store


def _resolve_feature_flag_store(deps) -> SystemFeatureFlagStore:
    existing = getattr(deps, "feature_flag_store", None)
    if existing is not None:
        return existing
    kb_store = getattr(deps, "kb_store", None)
    db_path = str(getattr(kb_store, "db_path", "") or "")
    store = SystemFeatureFlagStore(db_path=db_path or None)
    try:
        setattr(deps, "feature_flag_store", store)
    except Exception:
        pass
    return store


def _assert_paper_plag_enabled(ctx: AuthContextDep) -> None:
    try:
        enabled = _resolve_feature_flag_store(ctx.deps).is_enabled(FLAG_PAPER_PLAG_ENABLED, default=True)
    except Exception:
        enabled = True
    if not enabled:
        raise HTTPException(status_code=503, detail="feature_disabled:paper_plag")


def _quota_deps_with_store(ctx: AuthContextDep, *, store: PaperPlagStore):
    deps = ctx.deps
    if hasattr(deps, "paper_plag_store"):
        return deps
    return SimpleNamespace(
        nas_task_store=getattr(deps, "nas_task_store", None),
        data_security_store=getattr(deps, "data_security_store", None),
        paper_download_store=getattr(deps, "paper_download_store", None),
        patent_download_store=getattr(deps, "patent_download_store", None),
        kb_store=getattr(deps, "kb_store", None),
        paper_plag_store=store,
    )


def _raise_paper_plag_http_error(exc: RuntimeError) -> None:
    detail = str(exc or "")
    lowered = detail.lower()
    if "not_found" in lowered or "report_not_found" in lowered:
        raise HTTPException(status_code=404, detail=detail) from exc
    if (
        "required" in lowered
        or "invalid" in lowered
        or "unsupported" in lowered
    ):
        raise HTTPException(status_code=400, detail=detail) from exc
    if "quota_exceeded" in lowered:
        raise HTTPException(status_code=409, detail=detail) from exc
    if "feature_disabled" in lowered:
        raise HTTPException(status_code=503, detail=detail) from exc
    raise HTTPException(status_code=409, detail=detail or "paper_plag_operation_failed") from exc


@router.post("/paper-plag/reports/start")
async def start_paper_plag_report(body: PaperPlagStartRequest, ctx: AuthContextDep) -> dict[str, Any]:
    _assert_paper_plag_enabled(ctx)
    store = _resolve_store(ctx.deps)
    quota_deps = _quota_deps_with_store(ctx, store=store)
    try:
        UnifiedTaskQuotaService().assert_can_start(
            deps=quota_deps,
            actor_user_id=str(getattr(ctx.payload, "sub", "") or ""),
            task_kind=UnifiedTaskQuotaService.PAPER_PLAG_KIND,
        )
        service = PaperPlagiarismService(store=store)
        return await service.start_report(
            actor_user_id=str(getattr(ctx.payload, "sub", "") or ""),
            paper_id=body.paper_id,
            title=body.title,
            content_text=body.content_text,
            note=body.note,
            sources=[item.model_dump() for item in body.sources],
            similarity_threshold=body.similarity_threshold,
            priority=body.priority,
        )
    except RuntimeError as exc:
        _raise_paper_plag_http_error(exc)


@router.get("/paper-plag/reports/{report_id}")
async def get_paper_plag_report(report_id: str, ctx: AuthContextDep) -> dict[str, Any]:
    _assert_paper_plag_enabled(ctx)
    store = _resolve_store(ctx.deps)
    service = PaperPlagiarismService(store=store)
    try:
        return service.get_report(report_id)
    except RuntimeError as exc:
        _raise_paper_plag_http_error(exc)


@router.get("/paper-plag/reports")
async def list_paper_plag_reports(
    ctx: AuthContextDep,
    paper_id: str | None = Query(None),
    status: str | None = Query(None, description="comma separated statuses"),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    _assert_paper_plag_enabled(ctx)
    store = _resolve_store(ctx.deps)
    service = PaperPlagiarismService(store=store)
    statuses = None
    if status:
        statuses = [item.strip() for item in str(status).split(",") if item.strip()]
    return service.list_reports(
        limit=limit,
        paper_id=paper_id,
        statuses=statuses,
    )


@router.post("/paper-plag/reports/{report_id}/cancel")
async def cancel_paper_plag_report(report_id: str, ctx: AuthContextDep) -> dict[str, Any]:
    _assert_paper_plag_enabled(ctx)
    store = _resolve_store(ctx.deps)
    service = PaperPlagiarismService(store=store)
    try:
        return await service.cancel_report(report_id)
    except RuntimeError as exc:
        _raise_paper_plag_http_error(exc)


@router.post("/paper-plag/papers/{paper_id}/versions/save")
async def save_paper_version(
    paper_id: str,
    body: PaperVersionSaveRequest,
    ctx: AuthContextDep,
) -> dict[str, Any]:
    _assert_paper_plag_enabled(ctx)
    store = _resolve_store(ctx.deps)
    service = PaperPlagiarismService(store=store)
    try:
        return service.save_version(
            actor_user_id=str(getattr(ctx.payload, "sub", "") or ""),
            paper_id=paper_id,
            title=body.title,
            content_text=body.content_text,
            note=body.note,
        )
    except RuntimeError as exc:
        _raise_paper_plag_http_error(exc)


@router.get("/paper-plag/papers/{paper_id}/versions")
async def list_paper_versions(
    paper_id: str,
    ctx: AuthContextDep,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    _assert_paper_plag_enabled(ctx)
    store = _resolve_store(ctx.deps)
    service = PaperPlagiarismService(store=store)
    try:
        return service.list_versions(paper_id=paper_id, limit=limit)
    except RuntimeError as exc:
        _raise_paper_plag_http_error(exc)


@router.get("/paper-plag/papers/{paper_id}/versions/{version_id}")
async def get_paper_version(
    paper_id: str,
    version_id: int,
    ctx: AuthContextDep,
) -> dict[str, Any]:
    _assert_paper_plag_enabled(ctx)
    store = _resolve_store(ctx.deps)
    service = PaperPlagiarismService(store=store)
    try:
        return service.get_version(paper_id=paper_id, version_id=version_id)
    except RuntimeError as exc:
        _raise_paper_plag_http_error(exc)


@router.post("/paper-plag/papers/{paper_id}/versions/diff")
async def diff_paper_versions(
    paper_id: str,
    body: PaperVersionDiffRequest,
    ctx: AuthContextDep,
) -> dict[str, Any]:
    _assert_paper_plag_enabled(ctx)
    store = _resolve_store(ctx.deps)
    service = PaperPlagiarismService(store=store)
    try:
        return service.compare_versions(
            paper_id=paper_id,
            from_version_id=body.from_version_id,
            to_version_id=body.to_version_id,
        )
    except RuntimeError as exc:
        _raise_paper_plag_http_error(exc)


@router.post("/paper-plag/papers/{paper_id}/versions/{version_id}/rollback")
async def rollback_paper_version(
    paper_id: str,
    version_id: int,
    body: PaperVersionRollbackRequest,
    ctx: AuthContextDep,
) -> dict[str, Any]:
    _assert_paper_plag_enabled(ctx)
    store = _resolve_store(ctx.deps)
    service = PaperPlagiarismService(store=store)
    try:
        return service.rollback_version(
            actor_user_id=str(getattr(ctx.payload, "sub", "") or ""),
            paper_id=paper_id,
            version_id=version_id,
            note=body.note,
        )
    except RuntimeError as exc:
        _raise_paper_plag_http_error(exc)


@router.get("/paper-plag/reports/{report_id}/export")
async def export_paper_plag_report(
    report_id: str,
    ctx: AuthContextDep,
    format: str = Query("md"),
) -> Response:
    _assert_paper_plag_enabled(ctx)
    store = _resolve_store(ctx.deps)
    service = PaperPlagiarismService(store=store)
    try:
        payload = service.export_report(report_id, file_format=format)
    except RuntimeError as exc:
        _raise_paper_plag_http_error(exc)
    filename = str(payload.get("filename") or f"paper_plag_report_{report_id}.md")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(
        content=str(payload.get("content") or "").encode("utf-8"),
        media_type=str(payload.get("content_type") or "text/plain; charset=utf-8"),
        headers=headers,
    )

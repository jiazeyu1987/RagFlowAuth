from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.authz import AuthContextDep
from backend.services.permission_decision_service import PermissionDecisionError, PermissionDecisionService
from backend.services.task_control_service import TaskControlService

router = APIRouter()
permission_decider = PermissionDecisionService()


def _raise_task_http_error(exc: RuntimeError) -> None:
    detail = str(exc)
    lowered = detail.lower()
    if "暂不支持的任务类型" in detail or "unsupported task" in lowered or "unsupported task status" in lowered:
        raise HTTPException(status_code=400, detail=detail) from exc
    status_code = 404 if ("不存在" in detail or "not found" in lowered) else 409
    raise HTTPException(status_code=status_code, detail=detail) from exc


def _ensure_admin(ctx: AuthContextDep) -> None:
    try:
        permission_decider.ensure_admin(ctx.snapshot)
    except PermissionDecisionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.reason) from exc


@router.get("/tasks/metrics")
async def get_task_metrics(
    ctx: AuthContextDep,
    kind: str = Query(
        "all",
        description="Task kind: all/collection/nas_import/backup_job/paper_download/patent_download/paper_plagiarism/knowledge_upload",
    ),
):
    _ensure_admin(ctx)
    service = TaskControlService()
    try:
        return await service.get_metrics(deps=ctx.deps, task_kind=kind)
    except RuntimeError as exc:
        _raise_task_http_error(exc)


@router.get("/tasks")
async def list_tasks(
    ctx: AuthContextDep,
    kind: str = Query(
        "all",
        description="Task kind: all/collection/nas_import/backup_job/paper_download/patent_download/paper_plagiarism/knowledge_upload",
    ),
    status: str | None = Query(None, description="Unified status filter, comma-separated"),
    limit: int = Query(50, ge=1, le=200),
):
    _ensure_admin(ctx)
    service = TaskControlService()
    try:
        return await service.list_tasks(deps=ctx.deps, ctx=ctx, task_kind=kind, status=status, limit=limit)
    except RuntimeError as exc:
        _raise_task_http_error(exc)


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    ctx: AuthContextDep,
    kind: str = Query(
        "auto",
        description="Task kind: auto/collection/nas_import/backup_job/paper_download/patent_download/paper_plagiarism/knowledge_upload",
    ),
):
    _ensure_admin(ctx)
    service = TaskControlService()
    try:
        return await service.get_task(task_id, deps=ctx.deps, ctx=ctx, task_kind=kind)
    except RuntimeError as exc:
        _raise_task_http_error(exc)


@router.post("/tasks/{task_id}/pause")
async def pause_task(
    task_id: str,
    ctx: AuthContextDep,
    kind: str = Query(
        "auto",
        description="Task kind: auto/collection/nas_import/backup_job/paper_download/patent_download/paper_plagiarism/knowledge_upload",
    ),
):
    _ensure_admin(ctx)
    service = TaskControlService()
    try:
        return await service.pause_task(task_id, deps=ctx.deps, task_kind=kind)
    except RuntimeError as exc:
        _raise_task_http_error(exc)


@router.post("/tasks/{task_id}/resume")
async def resume_task(
    task_id: str,
    ctx: AuthContextDep,
    kind: str = Query(
        "auto",
        description="Task kind: auto/collection/nas_import/backup_job/paper_download/patent_download/paper_plagiarism/knowledge_upload",
    ),
):
    _ensure_admin(ctx)
    service = TaskControlService()
    try:
        return await service.resume_task(task_id, deps=ctx.deps, ctx=ctx, task_kind=kind)
    except RuntimeError as exc:
        _raise_task_http_error(exc)


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    ctx: AuthContextDep,
    kind: str = Query(
        "auto",
        description="Task kind: auto/collection/nas_import/backup_job/paper_download/patent_download/paper_plagiarism/knowledge_upload",
    ),
):
    _ensure_admin(ctx)
    service = TaskControlService()
    try:
        return await service.cancel_task(task_id, deps=ctx.deps, ctx=ctx, task_kind=kind)
    except RuntimeError as exc:
        _raise_task_http_error(exc)


@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: str,
    ctx: AuthContextDep,
    kind: str = Query(
        "auto",
        description="Task kind: auto/collection/nas_import/backup_job/paper_download/patent_download/paper_plagiarism/knowledge_upload",
    ),
):
    _ensure_admin(ctx)
    service = TaskControlService()
    try:
        return await service.retry_task(task_id, deps=ctx.deps, ctx=ctx, task_kind=kind)
    except RuntimeError as exc:
        _raise_task_http_error(exc)




from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.core.auth import get_deps
from backend.app.core.authz import AdminOnly
from backend.app.core.training_support import assert_user_training_for_action
from backend.app.dependencies import AppDependencies
from backend.app.modules.data_security.runner import start_job_if_idle
from backend.app.modules.data_security.support import (
    _actor_fields,
    _assert_backup_prerequisites,
    _audit_data_security_event,
    _backup_pack_stats,
    _backup_run_error_status,
    _hydrate_job_package_hash,
    _parse_real_restore_request,
    _parse_restore_drill_request,
    _request_audit_fields,
    _settings_response,
)
from backend.services.data_security import RealRestoreExecutionService, RestoreDrillExecutionService

router = APIRouter()


@router.get("/admin/data-security/settings")
def get_settings(_: AdminOnly, deps: AppDependencies = Depends(get_deps)) -> dict[str, Any]:
    store = deps.data_security_store
    s = store.get_settings()
    return _settings_response(s)


@router.put("/admin/data-security/settings")
def update_settings(
    payload: AdminOnly,
    request: Request,
    body: dict[str, Any],
    deps: AppDependencies = Depends(get_deps),
) -> dict[str, Any]:
    store = deps.data_security_store
    before = store.get_settings()
    change_reason = str((body or {}).get("change_reason") or "").strip()
    if not change_reason:
        raise HTTPException(status_code=400, detail="change_reason_required")
    changed_keys = sorted(k for k in (body or {}).keys() if k != "change_reason")
    if not changed_keys:
        raise HTTPException(status_code=400, detail="no_settings_changes")
    try:
        s = store.update_settings(body or {}, changed_by=payload.sub, change_reason=change_reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    resp = _settings_response(s)

    _audit_data_security_event(
        deps=deps,
        request=request,
        actor_user_id=payload.sub,
        action="data_security_settings_update",
        resource_type="data_security_settings",
        resource_id="1",
        event_type="update",
        before=asdict(before),
        after=asdict(s),
        reason=change_reason,
        meta={"changed_keys": changed_keys},
    )
    return resp


@router.post("/admin/data-security/backup/run")
def run_backup(
    payload: AdminOnly,
    request: Request,
    deps: AppDependencies = Depends(get_deps),
) -> dict[str, Any]:
    try:
        _assert_backup_prerequisites(deps)
        job_id = start_job_if_idle(reason="manual", store=deps.data_security_store)
    except RuntimeError as e:
        detail = str(e)
        raise HTTPException(status_code=_backup_run_error_status(detail), detail=detail)

    _audit_data_security_event(
        deps=deps,
        request=request,
        actor_user_id=payload.sub,
        action="backup_run",
        resource_type="backup_job",
        resource_id=str(job_id),
        event_type="create",
        before=None,
        after={"job_id": job_id, "kind": "incremental"},
        reason="manual_run",
        meta={"full_backup": False},
    )
    return {"job_id": job_id}


@router.get("/admin/data-security/backup/jobs")
def list_jobs(_: AdminOnly, limit: int = 30, deps: AppDependencies = Depends(get_deps)) -> dict[str, Any]:
    store = deps.data_security_store
    jobs = [_hydrate_job_package_hash(store, job) for job in store.list_jobs(limit=limit)]
    return {"jobs": [j.as_dict() for j in jobs]}


@router.get("/admin/data-security/backup/jobs/{job_id}")
def get_job(_: AdminOnly, job_id: int, deps: AppDependencies = Depends(get_deps)) -> dict[str, Any]:
    store = deps.data_security_store
    try:
        job = _hydrate_job_package_hash(store, store.get_job(job_id))
    except KeyError:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job.as_dict()


@router.post("/admin/data-security/backup/run-full")
def run_full_backup(
    payload: AdminOnly,
    request: Request,
    deps: AppDependencies = Depends(get_deps),
) -> dict[str, Any]:
    """Run a full backup including Docker images, containers, and networks."""
    try:
        _assert_backup_prerequisites(deps)
        job_id = start_job_if_idle(reason="manual_full_backup", store=deps.data_security_store, full_backup=True)
    except RuntimeError as e:
        detail = str(e)
        raise HTTPException(status_code=_backup_run_error_status(detail), detail=detail)

    _audit_data_security_event(
        deps=deps,
        request=request,
        actor_user_id=payload.sub,
        action="backup_run",
        resource_type="backup_job",
        resource_id=str(job_id),
        event_type="create",
        before=None,
        after={"job_id": job_id, "kind": "full"},
        reason="manual_run_full",
        meta={"full_backup": True},
    )
    return {"job_id": job_id}


@router.post("/admin/data-security/backup/jobs/{job_id}/cancel")
def cancel_backup_job(
    payload: AdminOnly,
    request: Request,
    job_id: int,
    body: dict[str, Any] | None = None,
    deps: AppDependencies = Depends(get_deps),
) -> dict[str, Any]:
    """
    Request cooperative cancellation for a queued/running backup job.

    Notes:
    - Cancellation is best-effort; long-running docker operations will be interrupted at heartbeat checkpoints.
    - On success, the job will transition to `canceling` then `canceled`.
    """
    store = deps.data_security_store
    try:
        before_job = store.get_job(job_id)
        job = store.request_cancel_job(job_id, reason=(body or {}).get("reason"))
    except KeyError:
        raise HTTPException(status_code=404, detail="job_not_found")

    _audit_data_security_event(
        deps=deps,
        request=request,
        actor_user_id=payload.sub,
        action="backup_cancel",
        resource_type="backup_job",
        resource_id=str(job_id),
        event_type="update",
        before=before_job.as_dict(),
        after=job.as_dict(),
        reason=(body or {}).get("reason"),
        meta={"cancel_requested": True},
    )
    return job.as_dict()


@router.post("/admin/data-security/restore-drills")
def create_restore_drill(
    payload: AdminOnly,
    request: Request,
    body: dict[str, Any] | None = None,
    deps: AppDependencies = Depends(get_deps),
) -> dict[str, Any]:
    actor_user = deps.user_store.get_by_user_id(payload.sub)
    if not actor_user:
        raise HTTPException(status_code=401, detail="actor_user_not_found")
    assert_user_training_for_action(
        deps=deps,
        user=actor_user,
        controlled_action="restore_drill_execute",
    )
    try:
        request_data = _parse_restore_drill_request(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        drill = RestoreDrillExecutionService(deps.data_security_store).execute_drill(
            job_id=request_data.job_id,
            backup_path=request_data.backup_path,
            backup_hash=request_data.backup_hash,
            restore_target=request_data.restore_target,
            executed_by=payload.sub,
            executed_at_ms=request_data.executed_at_ms,
            verification_notes=request_data.verification_notes,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _audit_data_security_event(
        deps=deps,
        request=request,
        actor_user_id=payload.sub,
        action="backup_restore_drill_create",
        resource_type="restore_drill",
        resource_id=drill.drill_id,
        event_type="create",
        before=None,
        after=drill.as_dict(),
        reason=request_data.reason,
        meta={
            "job_id": request_data.job_id,
            "result": drill.result,
            "acceptance_status": drill.acceptance_status,
            "package_validation_status": drill.package_validation_status,
            "hash_match": drill.hash_match,
            "compare_match": drill.compare_match,
        },
    )
    return drill.as_dict()


@router.post("/admin/data-security/restore/run")
def run_real_restore(
    payload: AdminOnly,
    request: Request,
    body: dict[str, Any] | None = None,
    deps: AppDependencies = Depends(get_deps),
) -> dict[str, Any]:
    actor_user = deps.user_store.get_by_user_id(payload.sub)
    if not actor_user:
        raise HTTPException(status_code=401, detail="actor_user_not_found")
    assert_user_training_for_action(
        deps=deps,
        user=actor_user,
        controlled_action="restore_drill_execute",
    )
    try:
        request_data = _parse_real_restore_request(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = RealRestoreExecutionService(deps.data_security_store).execute_restore(
            job_id=request_data.job_id,
            backup_path=request_data.backup_path,
            backup_hash=request_data.backup_hash,
            change_reason=request_data.change_reason,
            confirmation_text=request_data.confirmation_text,
            executed_by=payload.sub,
            executed_at_ms=request_data.executed_at_ms,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _audit_data_security_event(
        deps=deps,
        request=request,
        actor_user_id=payload.sub,
        action="backup_restore_execute",
        resource_type="backup_job",
        resource_id=str(result.job_id),
        event_type="update",
        before=None,
        after=result.as_dict(),
        reason=request_data.change_reason,
        meta={
            "job_id": result.job_id,
            "hash_match": result.hash_match,
            "compare_match": result.compare_match,
            "live_auth_db_path": result.live_auth_db_path,
        },
    )
    return result.as_dict()


@router.get("/admin/data-security/restore-drills")
def list_restore_drills(
    payload: AdminOnly,
    request: Request,
    limit: int = 30,
    deps: AppDependencies = Depends(get_deps),
) -> dict[str, Any]:
    items = deps.data_security_store.list_restore_drills(limit=limit)

    _audit_data_security_event(
        deps=deps,
        request=request,
        actor_user_id=payload.sub,
        action="backup_restore_drill_list",
        resource_type="restore_drill",
        resource_id="*",
        event_type="query",
        before=None,
        after=None,
        reason="list_restore_drills",
        meta={"limit": int(limit), "count": len(items)},
    )
    return {"items": [item.as_dict() for item in items], "count": len(items)}

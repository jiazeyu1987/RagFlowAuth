from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.core.auth import get_deps
from backend.app.core.authz import AdminOnly
from backend.app.core.config import settings
from backend.app.core.training_support import assert_user_training_for_action
from backend.app.dependencies import AppDependencies
from backend.app.modules.data_security.runner import start_job_if_idle
from backend.services.audit_helpers import actor_fields_from_user
from backend.services.data_security import RestoreDrillExecutionService

router = APIRouter()


def _norm_path(s: str) -> str:
    text = str(s or "").replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    if len(text) > 1:
        text = text.rstrip("/")
    return text


def _backup_pack_stats(s) -> dict[str, Any]:
    target = None
    try:
        target = s.target_path()
    except Exception:
        target = None

    if not target:
        return {"backup_target_path": "", "backup_pack_count": 0}

    target_text = str(target)
    p = Path(target_text)
    target_norm = _norm_path(target_text)

    # Defensive mode: avoid request-path stat/iterdir on network mount to prevent
    # kernel D-state stalls when CIFS storage is unhealthy.
    if target_norm == "/mnt/replica" or target_norm.startswith("/mnt/replica/"):
        if not settings.DATA_SECURITY_SCAN_MOUNT_STATS:
            return {
                "backup_target_path": str(p),
                "backup_pack_count": 0,
                "backup_pack_count_skipped": True,
            }

    try:
        count = 0
        if p.exists() and p.is_dir():
            count = sum(1 for child in p.iterdir() if child.is_dir() and child.name.startswith("migration_pack_"))
        return {"backup_target_path": str(p), "backup_pack_count": int(count)}
    except Exception:
        return {"backup_target_path": str(p), "backup_pack_count": 0}


def _request_audit_fields(request: Request) -> tuple[str | None, str | None]:
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    client_ip = getattr(getattr(request, "client", None), "host", None)
    return request_id, client_ip


def _actor_fields(deps: AppDependencies, actor_user_id: str) -> dict[str, Any]:
    actor_user = deps.user_store.get_by_user_id(actor_user_id)
    if not actor_user:
        raise HTTPException(status_code=401, detail="actor_user_not_found")
    return actor_fields_from_user(deps, actor_user)


def _settings_response(s) -> dict[str, Any]:
    resp: dict[str, Any] = {
        "enabled": s.enabled,
        "interval_minutes": s.interval_minutes,
        "target_mode": s.target_mode,
        "target_ip": s.target_ip or "",
        "target_share_name": s.target_share_name or "",
        "target_subdir": s.target_subdir or "",
        "target_local_dir": s.target_local_dir or "",
        "ragflow_compose_path": s.ragflow_compose_path or "",
        "ragflow_project_name": s.ragflow_project_name or "",
        "ragflow_stop_services": s.ragflow_stop_services,
        "auth_db_path": s.auth_db_path,
        "updated_at_ms": s.updated_at_ms,
        "last_run_at_ms": s.last_run_at_ms,
        "full_backup_enabled": getattr(s, "full_backup_enabled", False),
        "full_backup_include_images": getattr(s, "full_backup_include_images", True),
        "incremental_schedule": getattr(s, "incremental_schedule", None),
        "full_backup_schedule": getattr(s, "full_backup_schedule", None),
        "replica_enabled": getattr(s, "replica_enabled", False),
        "replica_target_path": getattr(s, "replica_target_path") or "",
        "replica_subdir_format": getattr(s, "replica_subdir_format") or "flat",
        "backup_retention_max": int(getattr(s, "backup_retention_max", 30) or 30),
    }
    resp.update(_backup_pack_stats(s))
    return resp


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

    request_id, client_ip = _request_audit_fields(request)
    deps.audit_log_manager.log_event(
        action="data_security_settings_update",
        actor=payload.sub,
        source="data_security",
        resource_type="data_security_settings",
        resource_id="1",
        event_type="update",
        before=asdict(before),
        after=asdict(s),
        reason=change_reason,
        request_id=request_id,
        client_ip=client_ip,
        meta={"changed_keys": changed_keys},
        **_actor_fields(deps, payload.sub),
    )
    return resp


@router.post("/admin/data-security/backup/run")
def run_backup(
    payload: AdminOnly,
    request: Request,
    deps: AppDependencies = Depends(get_deps),
) -> dict[str, Any]:
    try:
        job_id = start_job_if_idle(reason="manual", store=deps.data_security_store)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

    request_id, client_ip = _request_audit_fields(request)
    deps.audit_log_manager.log_event(
        action="backup_run",
        actor=payload.sub,
        source="data_security",
        resource_type="backup_job",
        resource_id=str(job_id),
        event_type="create",
        before=None,
        after={"job_id": job_id, "kind": "incremental"},
        reason="manual_run",
        request_id=request_id,
        client_ip=client_ip,
        meta={"full_backup": False},
        **_actor_fields(deps, payload.sub),
    )
    return {"job_id": job_id}


@router.get("/admin/data-security/backup/jobs")
def list_jobs(_: AdminOnly, limit: int = 30, deps: AppDependencies = Depends(get_deps)) -> dict[str, Any]:
    store = deps.data_security_store
    jobs = store.list_jobs(limit=limit)
    return {"jobs": [j.as_dict() for j in jobs]}


@router.get("/admin/data-security/backup/jobs/{job_id}")
def get_job(_: AdminOnly, job_id: int, deps: AppDependencies = Depends(get_deps)) -> dict[str, Any]:
    store = deps.data_security_store
    try:
        job = store.get_job(job_id)
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
        job_id = start_job_if_idle(reason="manual_full_backup", store=deps.data_security_store, full_backup=True)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

    request_id, client_ip = _request_audit_fields(request)
    deps.audit_log_manager.log_event(
        action="backup_run",
        actor=payload.sub,
        source="data_security",
        resource_type="backup_job",
        resource_id=str(job_id),
        event_type="create",
        before=None,
        after={"job_id": job_id, "kind": "full"},
        reason="manual_run_full",
        request_id=request_id,
        client_ip=client_ip,
        meta={"full_backup": True},
        **_actor_fields(deps, payload.sub),
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

    request_id, client_ip = _request_audit_fields(request)
    deps.audit_log_manager.log_event(
        action="backup_cancel",
        actor=payload.sub,
        source="data_security",
        resource_type="backup_job",
        resource_id=str(job_id),
        event_type="update",
        before=before_job.as_dict(),
        after=job.as_dict(),
        reason=(body or {}).get("reason"),
        request_id=request_id,
        client_ip=client_ip,
        meta={"cancel_requested": True},
        **_actor_fields(deps, payload.sub),
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
    data = body or {}

    try:
        job_id = int(data.get("job_id"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_job_id") from exc

    backup_path = str(data.get("backup_path") or "").strip()
    backup_hash = str(data.get("backup_hash") or "").strip()
    restore_target = str(data.get("restore_target") or "").strip()
    verification_notes = data.get("verification_notes")
    if verification_notes is not None:
        verification_notes = str(verification_notes).strip()

    if not backup_path:
        raise HTTPException(status_code=400, detail="backup_path_required")
    if not backup_hash:
        raise HTTPException(status_code=400, detail="backup_hash_required")
    if not restore_target:
        raise HTTPException(status_code=400, detail="restore_target_required")

    executed_at_raw = data.get("executed_at_ms")
    try:
        executed_at_ms = int(time.time() * 1000) if executed_at_raw is None else int(executed_at_raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_executed_at_ms") from exc

    try:
        drill = RestoreDrillExecutionService(deps.data_security_store).execute_drill(
            job_id=job_id,
            backup_path=backup_path,
            backup_hash=backup_hash,
            restore_target=restore_target,
            executed_by=payload.sub,
            executed_at_ms=executed_at_ms,
            verification_notes=verification_notes,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    request_id, client_ip = _request_audit_fields(request)
    deps.audit_log_manager.log_event(
        action="backup_restore_drill_create",
        actor=payload.sub,
        source="data_security",
        resource_type="restore_drill",
        resource_id=drill.drill_id,
        event_type="create",
        before=None,
        after=drill.as_dict(),
        reason=str(data.get("reason") or "manual_restore_drill"),
        request_id=request_id,
        client_ip=client_ip,
        meta={
            "job_id": job_id,
            "result": drill.result,
            "acceptance_status": drill.acceptance_status,
            "package_validation_status": drill.package_validation_status,
            "hash_match": drill.hash_match,
            "compare_match": drill.compare_match,
        },
        **_actor_fields(deps, payload.sub),
    )
    return drill.as_dict()


@router.get("/admin/data-security/restore-drills")
def list_restore_drills(
    payload: AdminOnly,
    request: Request,
    limit: int = 30,
    deps: AppDependencies = Depends(get_deps),
) -> dict[str, Any]:
    items = deps.data_security_store.list_restore_drills(limit=limit)

    request_id, client_ip = _request_audit_fields(request)
    deps.audit_log_manager.log_event(
        action="backup_restore_drill_list",
        actor=payload.sub,
        source="data_security",
        resource_type="restore_drill",
        resource_id="*",
        event_type="query",
        before=None,
        after=None,
        reason="list_restore_drills",
        request_id=request_id,
        client_ip=client_ip,
        meta={"limit": int(limit), "count": len(items)},
        **_actor_fields(deps, payload.sub),
    )
    return {"items": [item.as_dict() for item in items], "count": len(items)}

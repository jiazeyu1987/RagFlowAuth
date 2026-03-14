from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.modules.data_security.runner import start_job_if_idle
from backend.services.feature_visibility import (
    assert_feature_visible_or_404,
    resolve_feature_visibility_store,
)
from backend.services.feature_visibility_store import FLAG_API_ADMIN_FEATURE_FLAGS_VISIBLE
from backend.services.egress_decision_audit_store import EgressDecisionAuditStore
from backend.services.egress_mode_runtime import clear_egress_policy_cache
from backend.services.data_security_store import DataSecurityStore
from backend.services.egress_policy_store import EgressPolicyStore
from backend.services.system_feature_flag_store import SystemFeatureFlagStore

router = APIRouter()


def _backup_pack_stats(s) -> dict[str, Any]:
    target = None
    try:
        target = s.target_path()
    except Exception:
        target = None

    if not target:
        return {"backup_target_path": "", "backup_pack_count": 0}

    p = Path(str(target))
    try:
        count = 0
        if p.exists() and p.is_dir():
            count = sum(1 for child in p.iterdir() if child.is_dir() and child.name.startswith("migration_pack_"))
        return {"backup_target_path": str(p), "backup_pack_count": int(count)}
    except Exception:
        return {"backup_target_path": str(p), "backup_pack_count": 0}


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


@router.get("/admin/data-security/settings")
async def get_settings(_: AdminOnly) -> dict[str, Any]:
    store = DataSecurityStore()
    s = store.get_settings()
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
        "full_backup_enabled": getattr(s, 'full_backup_enabled', False),
        "full_backup_include_images": getattr(s, 'full_backup_include_images', True),
        "incremental_schedule": getattr(s, 'incremental_schedule', None),
        "full_backup_schedule": getattr(s, 'full_backup_schedule', None),
        "replica_enabled": getattr(s, 'replica_enabled', False),
        "replica_target_path": getattr(s, 'replica_target_path') or "",
        "replica_subdir_format": getattr(s, 'replica_subdir_format') or "flat",
        "backup_retention_max": int(getattr(s, "backup_retention_max", 30) or 30),
    }
    resp.update(_backup_pack_stats(s))
    return resp


@router.put("/admin/data-security/settings")
async def update_settings(_: AdminOnly, body: dict[str, Any]) -> dict[str, Any]:
    store = DataSecurityStore()
    s = store.update_settings(body or {})
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
        "full_backup_enabled": getattr(s, 'full_backup_enabled', False),
        "full_backup_include_images": getattr(s, 'full_backup_include_images', True),
        "incremental_schedule": getattr(s, 'incremental_schedule', None),
        "full_backup_schedule": getattr(s, 'full_backup_schedule', None),
        "replica_enabled": getattr(s, 'replica_enabled', False),
        "replica_target_path": getattr(s, 'replica_target_path') or "",
        "replica_subdir_format": getattr(s, 'replica_subdir_format') or "flat",
        "backup_retention_max": int(getattr(s, "backup_retention_max", 30) or 30),
    }
    resp.update(_backup_pack_stats(s))
    return resp


@router.post("/admin/data-security/backup/run")
async def run_backup(admin: AdminOnly) -> dict[str, Any]:
    try:
        job_id = start_job_if_idle(reason="手动", actor_user_id=str(getattr(admin, "sub", "") or ""))
        return {"job_id": job_id}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/admin/data-security/backup/jobs")
async def list_jobs(_: AdminOnly, limit: int = 30) -> dict[str, Any]:
    store = DataSecurityStore()
    jobs = store.list_jobs(limit=limit)
    return {"jobs": [j.as_dict() for j in jobs]}


@router.get("/admin/data-security/backup/jobs/{job_id}")
async def get_job(_: AdminOnly, job_id: int) -> dict[str, Any]:
    store = DataSecurityStore()
    try:
        job = store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job.as_dict()


@router.post("/admin/data-security/backup/run-full")
async def run_full_backup(admin: AdminOnly) -> dict[str, Any]:
    """Run a full backup including Docker images, containers, and networks"""
    try:
        job_id = start_job_if_idle(reason="手动全量备份", full_backup=True, actor_user_id=str(getattr(admin, "sub", "") or ""))
        return {"job_id": job_id}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/admin/data-security/backup/jobs/{job_id}/cancel")
async def cancel_backup_job(_: AdminOnly, job_id: int, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Request cooperative cancellation for a queued/running backup job.

    Notes:
    - Cancellation is best-effort; long-running docker operations will be interrupted at heartbeat checkpoints.
    - On success, the job will transition to `canceling` then `canceled`.
    """
    store = DataSecurityStore()
    try:
        job = store.request_cancel_job(job_id, reason=(body or {}).get("reason"))
    except KeyError:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job.as_dict()


@router.get("/admin/security/egress/config")
async def get_egress_policy_config(_: AdminOnly) -> dict[str, Any]:
    store = EgressPolicyStore()
    settings_obj = store.get()
    return settings_obj.as_dict()


@router.put("/admin/security/egress/config")
async def update_egress_policy_config(admin: AdminOnly, body: dict[str, Any] | None = None) -> dict[str, Any]:
    store = EgressPolicyStore()
    try:
        settings_obj = store.update(body or {}, actor_user_id=str(getattr(admin, "sub", "") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    clear_egress_policy_cache()
    return settings_obj.as_dict()


@router.get("/admin/security/egress/audits")
async def list_egress_decision_audits(
    _: AdminOnly,
    limit: int = 100,
    decision: str | None = None,
    actor_user_id: str | None = None,
    target_host: str | None = None,
    since_ms: int | None = None,
    until_ms: int | None = None,
) -> dict[str, Any]:
    store = EgressDecisionAuditStore()
    safe_limit = max(1, min(int(limit or 100), 500))
    records = store.list_decisions(
        limit=safe_limit,
        decision=decision,
        actor_user_id=actor_user_id,
        target_host=target_host,
        since_ms=since_ms,
        until_ms=until_ms,
    )
    return {
        "limit": safe_limit,
        "total": len(records),
        "items": [item.as_dict() for item in records],
    }


@router.get("/security/feature-flags")
async def get_feature_flags(ctx: AuthContextDep) -> dict[str, Any]:
    store = _resolve_feature_flag_store(ctx.deps)
    payload = store.list_flags()
    payload.update(resolve_feature_visibility_store(ctx.deps).list_flags())
    return payload


@router.get("/admin/security/feature-flags")
async def get_admin_feature_flags(_: AdminOnly, ctx: AuthContextDep) -> dict[str, Any]:
    assert_feature_visible_or_404(
        deps=ctx.deps,
        user=ctx.user,
        flag_key=FLAG_API_ADMIN_FEATURE_FLAGS_VISIBLE,
    )
    return SystemFeatureFlagStore().list_flags()


@router.put("/admin/security/feature-flags")
async def update_feature_flags(admin: AdminOnly, ctx: AuthContextDep, body: dict[str, Any] | None = None) -> dict[str, Any]:
    assert_feature_visible_or_404(
        deps=ctx.deps,
        user=ctx.user,
        flag_key=FLAG_API_ADMIN_FEATURE_FLAGS_VISIBLE,
    )
    store = SystemFeatureFlagStore()
    try:
        payload = store.update_flags(body or {}, actor_user_id=str(getattr(admin, "sub", "") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    clear_egress_policy_cache()
    return payload


@router.post("/admin/security/feature-flags/rollback-disable")
async def rollback_disable_feature_flags(admin: AdminOnly, ctx: AuthContextDep) -> dict[str, Any]:
    assert_feature_visible_or_404(
        deps=ctx.deps,
        user=ctx.user,
        flag_key=FLAG_API_ADMIN_FEATURE_FLAGS_VISIBLE,
    )
    store = SystemFeatureFlagStore()
    payload = store.rollback_disable_all(actor_user_id=str(getattr(admin, "sub", "") or ""))
    clear_egress_policy_cache()
    return payload


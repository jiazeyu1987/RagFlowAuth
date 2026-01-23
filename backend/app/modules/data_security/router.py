from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AdminOnly
from backend.app.modules.data_security.runner import start_job_if_idle
from backend.services.data_security_store import DataSecurityStore

router = APIRouter()


@router.get("/admin/data-security/settings")
async def get_settings(_: AdminOnly) -> dict[str, Any]:
    store = DataSecurityStore()
    s = store.get_settings()
    return {
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
    }


@router.put("/admin/data-security/settings")
async def update_settings(_: AdminOnly, body: dict[str, Any]) -> dict[str, Any]:
    store = DataSecurityStore()
    s = store.update_settings(body or {})
    return {
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
    }


@router.post("/admin/data-security/backup/run")
async def run_backup(_: AdminOnly) -> dict[str, Any]:
    job_id = start_job_if_idle(reason="手动")
    return {"job_id": job_id}


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
async def run_full_backup(_: AdminOnly) -> dict[str, Any]:
    """Run a full backup including Docker images, containers, and networks"""
    job_id = start_job_if_idle(reason="手动全量备份", full_backup=True)
    return {"job_id": job_id}



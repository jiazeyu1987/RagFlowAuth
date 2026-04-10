from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

from fastapi import HTTPException, Request

from backend.app.core.config import settings
from backend.app.core.paths import repo_root
from backend.app.dependencies import AppDependencies
from backend.services.audit_helpers import actor_fields_from_user
from backend.services.data_security.backup_service import _compute_backup_package_hash
from backend.services.data_security.docker_utils import (
    docker_ok,
    list_docker_volumes_by_prefix,
    read_compose_project_name,
    resolve_backend_helper_image,
)
from backend.services.data_security.models import (
    STANDARD_NAS_MOUNT_ROOT,
    is_standard_nas_path,
    resolve_runtime_compose_file_path,
)
from backend.services.mount_utils import is_cifs_mounted


@dataclass(frozen=True)
class RestoreDrillRequestData:
    job_id: int
    backup_path: str
    backup_hash: str
    restore_target: str
    executed_at_ms: int
    verification_notes: str | None
    reason: str


@dataclass(frozen=True)
class RealRestoreRequestData:
    job_id: int
    backup_path: str
    backup_hash: str
    change_reason: str
    confirmation_text: str
    executed_at_ms: int


def _norm_path(value: str) -> str:
    text = str(value or "").replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    if len(text) > 1:
        text = text.rstrip("/")
    return text


def _pack_stats_for_target(target: str) -> dict[str, Any]:
    target_text = str(target or "").strip()
    if not target_text:
        return {"target_path": "", "pack_count": 0}

    path = Path(target_text)
    target_norm = _norm_path(target_text)

    if is_standard_nas_path(target_norm) or target_norm == "/mnt/replica" or target_norm.startswith("/mnt/replica/"):
        if not settings.DATA_SECURITY_SCAN_MOUNT_STATS:
            return {
                "target_path": str(path),
                "pack_count": 0,
                "pack_count_skipped": True,
            }

    try:
        count = 0
        if path.exists() and path.is_dir():
            count = sum(1 for child in path.iterdir() if child.is_dir() and child.name.startswith("migration_pack_"))
        return {"target_path": str(path), "pack_count": int(count)}
    except Exception:
        return {"target_path": str(path), "pack_count": 0}


def _backup_pack_stats(settings_obj: Any) -> dict[str, Any]:
    local_target = None
    try:
        local_target = settings_obj.local_backup_target_path()
    except Exception:
        local_target = None

    local_stats = _pack_stats_for_target(str(local_target or ""))
    return {
        "local_backup_target_path": local_stats["target_path"],
        "local_backup_pack_count": local_stats["pack_count"],
        "local_backup_pack_count_skipped": local_stats.get("pack_count_skipped", False),
        "windows_backup_target_path": "",
        "windows_backup_pack_count": 0,
        "windows_backup_pack_count_skipped": False,
    }


def _settings_response(settings_obj: Any) -> dict[str, Any]:
    response: dict[str, Any] = {
        "enabled": settings_obj.enabled,
        "interval_minutes": settings_obj.interval_minutes,
        "target_mode": settings_obj.target_mode,
        "target_ip": settings_obj.target_ip or "",
        "target_share_name": settings_obj.target_share_name or "",
        "target_subdir": settings_obj.target_subdir or "",
        "target_local_dir": settings_obj.target_local_dir or "",
        "ragflow_compose_path": settings_obj.ragflow_compose_path or "",
        "ragflow_project_name": settings_obj.ragflow_project_name or "",
        "ragflow_stop_services": settings_obj.ragflow_stop_services,
        "auth_db_path": settings_obj.auth_db_path,
        "updated_at_ms": settings_obj.updated_at_ms,
        "last_run_at_ms": settings_obj.last_run_at_ms,
        "full_backup_enabled": settings_obj.full_backup_enabled,
        "full_backup_include_images": settings_obj.full_backup_include_images,
        "incremental_schedule": settings_obj.incremental_schedule,
        "full_backup_schedule": settings_obj.full_backup_schedule,
        "replica_enabled": settings_obj.replica_enabled,
        "replica_target_path": settings_obj.replica_target_path or "",
        "replica_subdir_format": settings_obj.replica_subdir_format or "flat",
        "backup_retention_max": int(settings_obj.backup_retention_max or 30),
    }
    response.update(_backup_pack_stats(settings_obj))
    return response


def _resolve_auth_db_path(auth_db_path: str) -> Path:
    path = Path(str(auth_db_path or "").strip() or "data/auth.db")
    if not path.is_absolute():
        path = repo_root() / path
    return path


def _resolve_backup_worker_image(
    *, compose_file: Path | None = None, project_name: str | None = None
) -> tuple[str | None, str | None]:
    try:
        return resolve_backend_helper_image(compose_file=compose_file, project_name=project_name), None
    except RuntimeError as exc:
        return None, str(exc)


def _assert_backup_prerequisites(deps: AppDependencies) -> None:
    current_settings = deps.data_security_store.get_settings()
    local_target = str(current_settings.local_backup_target_path() or "").strip()
    if not local_target:
        raise RuntimeError("local_backup_target_not_configured")
    if is_standard_nas_path(local_target) and not is_cifs_mounted(STANDARD_NAS_MOUNT_ROOT):
        raise RuntimeError(f"local_backup_target_mount_not_cifs:{STANDARD_NAS_MOUNT_ROOT}")

    ok, why = docker_ok()
    if not ok:
        raise RuntimeError(f"docker_unavailable:{why}")

    local_root = Path(local_target)
    try:
        probe_dir = local_root / "_staging" / "_preflight"
        probe_dir.mkdir(parents=True, exist_ok=True)
        probe = probe_dir / f".write_probe_{int(time.time() * 1000)}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as exc:
        raise RuntimeError(f"local_backup_target_not_writable:{local_root} err={exc}") from exc

    source_auth_db = _resolve_auth_db_path(current_settings.auth_db_path)
    if not source_auth_db.exists():
        raise RuntimeError(f"project_auth_db_not_found:{source_auth_db}")

    compose_path = str(current_settings.ragflow_compose_path or "").strip()
    if not compose_path:
        raise RuntimeError("ragflow_compose_path_required")
    compose_file = resolve_runtime_compose_file_path(compose_path)
    if compose_file is None:
        raise RuntimeError("ragflow_compose_path_required")
    if not compose_file.exists():
        raise RuntimeError(f"ragflow_compose_file_not_found:{compose_file}")

    project_name = read_compose_project_name(compose_file)
    prefix = f"{project_name}_"
    volumes = list_docker_volumes_by_prefix(prefix)
    if not volumes:
        raise RuntimeError(f"ragflow_volumes_not_found:{prefix}")

    _, worker_error = _resolve_backup_worker_image(compose_file=compose_file, project_name=project_name)
    if worker_error:
        raise RuntimeError(worker_error)


def _request_audit_fields(request: Request) -> tuple[str | None, str | None]:
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    client_ip = getattr(getattr(request, "client", None), "host", None)
    return request_id, client_ip


def _actor_fields(deps: AppDependencies, actor_user_id: str) -> dict[str, Any]:
    actor_user = deps.user_store.get_by_user_id(actor_user_id)
    if not actor_user:
        raise HTTPException(status_code=401, detail="actor_user_not_found")
    return actor_fields_from_user(deps, actor_user)


def _audit_data_security_event(
    *,
    deps: AppDependencies,
    request: Request,
    actor_user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    event_type: str,
    before: Any,
    after: Any,
    reason: str | None,
    meta: dict[str, Any] | None = None,
) -> None:
    request_id, client_ip = _request_audit_fields(request)
    deps.audit_log_manager.log_event(
        action=action,
        actor=actor_user_id,
        source="data_security",
        resource_type=resource_type,
        resource_id=resource_id,
        event_type=event_type,
        before=before,
        after=after,
        reason=reason,
        request_id=request_id,
        client_ip=client_ip,
        meta=meta,
        **_actor_fields(deps, actor_user_id),
    )


def _hydrate_job_package_hash(store: Any, job: Any):
    if not job or job.package_hash or not str(job.output_dir or "").strip():
        return job
    pack_dir = Path(str(job.output_dir).strip())
    if not pack_dir.exists() or not pack_dir.is_dir():
        return job
    try:
        package_hash = _compute_backup_package_hash(pack_dir)
        return store.update_job(job.id, package_hash=package_hash)
    except Exception:
        return job


def _backup_run_error_status(detail: str) -> int:
    return 409 if detail == "backup_job_already_running" or "占用" in detail else 400


def _parse_restore_drill_request(body: dict[str, Any] | None) -> RestoreDrillRequestData:
    data = body or {}

    try:
        job_id = int(data.get("job_id"))
    except Exception as exc:
        raise ValueError("invalid_job_id") from exc

    backup_path = str(data.get("backup_path") or "").strip()
    backup_hash = str(data.get("backup_hash") or "").strip()
    restore_target = str(data.get("restore_target") or "").strip()
    verification_notes = data.get("verification_notes")
    if verification_notes is not None:
        verification_notes = str(verification_notes).strip()

    if not backup_path:
        raise ValueError("backup_path_required")
    if not backup_hash:
        raise ValueError("backup_hash_required")
    if not restore_target:
        raise ValueError("restore_target_required")

    executed_at_raw = data.get("executed_at_ms")
    try:
        executed_at_ms = int(time.time() * 1000) if executed_at_raw is None else int(executed_at_raw)
    except Exception as exc:
        raise ValueError("invalid_executed_at_ms") from exc

    return RestoreDrillRequestData(
        job_id=job_id,
        backup_path=backup_path,
        backup_hash=backup_hash,
        restore_target=restore_target,
        executed_at_ms=executed_at_ms,
        verification_notes=verification_notes,
        reason=str(data.get("reason") or "manual_restore_drill"),
    )


def _parse_real_restore_request(body: dict[str, Any] | None) -> RealRestoreRequestData:
    data = body or {}

    try:
        job_id = int(data.get("job_id"))
    except Exception as exc:
        raise ValueError("invalid_job_id") from exc

    backup_path = str(data.get("backup_path") or "").strip()
    backup_hash = str(data.get("backup_hash") or "").strip()
    change_reason = str(data.get("change_reason") or "").strip()
    confirmation_text = str(data.get("confirmation_text") or "").strip()

    if not backup_path:
        raise ValueError("backup_path_required")
    if not backup_hash:
        raise ValueError("backup_hash_required")
    if not change_reason:
        raise ValueError("change_reason_required")
    if not confirmation_text:
        raise ValueError("restore_confirmation_text_required")

    executed_at_raw = data.get("executed_at_ms")
    try:
        executed_at_ms = int(time.time() * 1000) if executed_at_raw is None else int(executed_at_raw)
    except Exception as exc:
        raise ValueError("invalid_executed_at_ms") from exc

    return RealRestoreRequestData(
        job_id=job_id,
        backup_path=backup_path,
        backup_hash=backup_hash,
        change_reason=change_reason,
        confirmation_text=confirmation_text,
        executed_at_ms=executed_at_ms,
    )

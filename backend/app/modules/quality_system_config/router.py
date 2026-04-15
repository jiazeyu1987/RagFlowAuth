from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import get_global_deps
from backend.app.core.authz import AdminOnly
from backend.app.dependencies import AppDependencies
from backend.models.quality_system_config import (
    QualitySystemAssignableUser,
    QualitySystemConfigResponse,
    QualitySystemCreateFileCategoryRequest,
    QualitySystemDeactivateFileCategoryRequest,
    QualitySystemFileCategory,
    QualitySystemPosition,
    QualitySystemUpdateAssignmentsRequest,
)
from backend.services.quality_system_config import QualitySystemConfigError, QualitySystemConfigService


router = APIRouter()


def _deps(deps: AppDependencies = Depends(get_global_deps)) -> AppDependencies:
    return deps


def _service(deps: AppDependencies) -> QualitySystemConfigService:
    return QualitySystemConfigService(
        db_path=getattr(getattr(deps, "user_store", None), "db_path", None),
        user_store=deps.user_store,
        org_structure_manager=deps.org_structure_manager,
        audit_log_manager=deps.audit_log_manager,
    )


def _actor_user(payload, deps: AppDependencies):
    user = deps.user_store.get_by_user_id(payload.sub)
    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")
    return user


def _handle_quality_system_config_error(exc: QualitySystemConfigError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.code)


@router.get("/admin/quality-system-config", response_model=QualitySystemConfigResponse)
async def get_quality_system_config(_: AdminOnly, deps: AppDependencies = Depends(_deps)):
    try:
        return _service(deps).get_config()
    except QualitySystemConfigError as exc:
        raise _handle_quality_system_config_error(exc) from exc


@router.get(
    "/admin/quality-system-config/users",
    response_model=list[QualitySystemAssignableUser],
)
async def search_quality_system_config_users(
    _: AdminOnly,
    deps: AppDependencies = Depends(_deps),
    q: str | None = None,
    limit: int = 20,
):
    try:
        return _service(deps).search_assignable_users(q=q, limit=limit)
    except QualitySystemConfigError as exc:
        raise _handle_quality_system_config_error(exc) from exc


@router.put(
    "/admin/quality-system-config/positions/{position_id}/assignments",
    response_model=QualitySystemPosition,
)
async def update_quality_system_position_assignments(
    position_id: int,
    body: QualitySystemUpdateAssignmentsRequest,
    payload: AdminOnly,
    deps: AppDependencies = Depends(_deps),
):
    try:
        return _service(deps).update_position_assignments(
            position_id=position_id,
            user_ids=body.user_ids,
            change_reason=body.change_reason,
            actor_user=_actor_user(payload, deps),
        )
    except QualitySystemConfigError as exc:
        raise _handle_quality_system_config_error(exc) from exc


@router.post(
    "/admin/quality-system-config/file-categories",
    response_model=QualitySystemFileCategory,
)
async def create_quality_system_file_category(
    body: QualitySystemCreateFileCategoryRequest,
    payload: AdminOnly,
    deps: AppDependencies = Depends(_deps),
):
    try:
        return _service(deps).create_file_category(
            name=body.name,
            change_reason=body.change_reason,
            actor_user=_actor_user(payload, deps),
        )
    except QualitySystemConfigError as exc:
        raise _handle_quality_system_config_error(exc) from exc


@router.post(
    "/admin/quality-system-config/file-categories/{category_id}/deactivate",
    response_model=QualitySystemFileCategory,
)
async def deactivate_quality_system_file_category(
    category_id: int,
    body: QualitySystemDeactivateFileCategoryRequest,
    payload: AdminOnly,
    deps: AppDependencies = Depends(_deps),
):
    try:
        return _service(deps).deactivate_file_category(
            category_id=category_id,
            change_reason=body.change_reason,
            actor_user=_actor_user(payload, deps),
        )
    except QualitySystemConfigError as exc:
        raise _handle_quality_system_config_error(exc) from exc

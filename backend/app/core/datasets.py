from __future__ import annotations

from backend.app.core.permission_resolver import PermissionSnapshot, filter_datasets_by_name
from backend.app.dependencies import AppDependencies
from fastapi import HTTPException


def list_accessible_datasets(deps: AppDependencies, snapshot: PermissionSnapshot) -> list[dict]:
    all_datasets = deps.ragflow_service.list_datasets()
    return filter_datasets_by_name(snapshot, all_datasets)


def list_visible_datasets(deps: AppDependencies, snapshot: PermissionSnapshot, user: object) -> list[dict]:
    if str(getattr(user, "role", "") or "") == "sub_admin":
        management_manager = getattr(deps, "knowledge_management_manager", None)
        if management_manager is None:
            raise HTTPException(status_code=500, detail="knowledge_management_manager_unavailable")
        try:
            datasets = management_manager.list_manageable_datasets(user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=int(getattr(exc, "status_code", 400) or 400),
                detail=str(exc),
            ) from exc
        if not isinstance(datasets, list):
            raise HTTPException(status_code=500, detail="invalid_manageable_datasets")
        return datasets
    return list_accessible_datasets(deps, snapshot)

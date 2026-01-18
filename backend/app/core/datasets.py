from __future__ import annotations

from backend.app.core.permission_resolver import PermissionSnapshot, filter_datasets_by_name
from backend.app.dependencies import AppDependencies


def list_accessible_datasets(deps: AppDependencies, snapshot: PermissionSnapshot) -> list[dict]:
    all_datasets = deps.ragflow_service.list_datasets()
    if snapshot.is_admin:
        return all_datasets
    return filter_datasets_by_name(snapshot, all_datasets)


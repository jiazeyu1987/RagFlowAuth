from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException

from backend.app.modules.permission_groups import access as permission_access
from backend.app.modules.permission_groups import contracts as permission_contracts


def run_group_management_action(ctx, operation: Callable[[], object]):
    permission_access.assert_group_management(ctx)
    return operation()


def run_group_resource_action(
    ctx,
    *,
    action: str,
    default_detail: str,
    loader: Callable[[], object],
    wrapper: Callable[[object], object],
):
    try:
        return run_group_management_action(ctx, lambda: wrapper(loader()))
    except HTTPException:
        raise
    except Exception as exc:
        permission_contracts.raise_resource_error(action, exc, default_detail=default_detail)


def get_visible_folder_ids(ctx, service) -> set[str]:
    _folder_snapshot, visible_folder_ids = permission_access.get_visible_folder_scope(ctx, service)
    return visible_folder_ids


def get_visible_folder_ids_for_target(ctx, service, *, folder_id: str) -> set[str]:
    visible_folder_ids = get_visible_folder_ids(ctx, service)
    permission_access.assert_folder_visible(folder_id, visible_folder_ids)
    return visible_folder_ids


def get_manageable_folder_ids(ctx, service) -> set[str]:
    _folder_snapshot, manageable_folder_ids = permission_access.get_writable_folder_scope(ctx, service)
    return manageable_folder_ids


def get_manageable_folder_ids_for_target(ctx, service, *, folder_id: str) -> set[str]:
    manageable_folder_ids = get_manageable_folder_ids(ctx, service)
    permission_access.assert_folder_manageable(folder_id, manageable_folder_ids)
    return manageable_folder_ids

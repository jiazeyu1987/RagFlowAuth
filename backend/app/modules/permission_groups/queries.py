from __future__ import annotations

from backend.app.modules.permission_groups import access as permission_access
from backend.app.modules.permission_groups import contracts as permission_contracts
from backend.app.modules.permission_groups import operations as permission_operations


def list_permission_groups_result(ctx, service):
    return permission_operations.run_group_management_action(
        ctx,
        lambda: permission_contracts.wrap_groups(permission_access.list_manageable_groups(ctx, service)),
    )


def list_assignable_permission_groups_result(ctx, service):
    groups = permission_access.list_assignable_groups(ctx, service)
    return permission_contracts.wrap_groups(groups)


def get_permission_group_result(ctx, service, group_id: int):
    return permission_operations.run_group_management_action(
        ctx,
        lambda: permission_contracts.wrap_group(permission_access.get_manageable_group(ctx, service, group_id)),
    )

from __future__ import annotations

from fastapi import HTTPException

from backend.app.modules.permission_groups import access as permission_access
from backend.app.modules.permission_groups import contracts as permission_contracts
from backend.app.modules.permission_groups import operations as permission_operations


def folder_snapshot_result(ctx, service):
    return permission_operations.run_group_resource_action(
        ctx,
        action="get permission group folders",
        default_detail="permission_group_folders_unavailable",
        loader=lambda: permission_access.list_manageable_folder_snapshot(ctx, service),
        wrapper=permission_contracts.wrap_folder_snapshot,
    )


def create_group_folder_result(ctx, service, data) -> dict:
    def create_folder():
        if data.parent_id:
            manageable_folder_ids = permission_operations.get_manageable_folder_ids(ctx, service)
            permission_access.validate_folder_parent(data.parent_id, manageable_folder_ids)
        folder = service.create_group_folder(name=data.name, parent_id=data.parent_id, created_by=ctx.user.user_id)
        folder = permission_contracts.require_object_payload(folder, detail="permission_group_folder_invalid_payload")
        return permission_contracts.wrap_folder(folder)

    return permission_operations.run_group_management_action(ctx, create_folder)


def update_group_folder_result(ctx, service, folder_id: str, data) -> dict:
    def update_folder():
        manageable_folder_ids = permission_operations.get_manageable_folder_ids_for_target(
            ctx,
            service,
            folder_id=folder_id,
        )
        payload = permission_access.build_group_folder_update_payload(data, visible_ids=manageable_folder_ids)
        folder = service.update_group_folder(folder_id, payload)
        folder = permission_contracts.require_object_payload(folder, detail="permission_group_folder_invalid_payload")
        return permission_contracts.wrap_folder(folder)

    return permission_operations.run_group_management_action(ctx, update_folder)


def delete_group_folder_result(ctx, service, folder_id: str) -> dict:
    def delete_folder():
        permission_operations.get_manageable_folder_ids_for_target(ctx, service, folder_id=folder_id)
        ok = service.delete_group_folder(folder_id)
        if not ok:
            raise HTTPException(status_code=404, detail="folder_not_found")
        return permission_contracts.wrap_result("permission_group_folder_deleted")

    return permission_operations.run_group_management_action(ctx, delete_folder)

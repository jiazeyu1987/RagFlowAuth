from __future__ import annotations

from fastapi import HTTPException

from backend.app.modules.permission_groups import access as permission_access
from backend.app.modules.permission_groups import contracts as permission_contracts
from backend.app.modules.permission_groups import operations as permission_operations
from backend.app.modules.permission_groups import payloads as permission_payloads


def require_group_create_result(group_id: object) -> int:
    if type(group_id) is not int:
        raise HTTPException(status_code=502, detail="permission_group_create_invalid_payload")
    return group_id


def require_group_update_result(success: object) -> None:
    if not success:
        raise HTTPException(status_code=400, detail="permission_group_update_failed")


def require_group_delete_result(success: object) -> None:
    if not success:
        raise HTTPException(status_code=400, detail="permission_group_delete_failed")


def create_permission_group_result(ctx, service, data) -> dict:
    def create_group():
        payload = permission_payloads.build_create_group_payload(data, created_by=ctx.user.user_id)
        permission_access.validate_group_scope(
            ctx,
            accessible_kbs=payload.get("accessible_kbs"),
            accessible_kb_nodes=payload.get("accessible_kb_nodes"),
            accessible_chats=payload.get("accessible_chats"),
        )
        group_id = require_group_create_result(service.create_group(payload))
        return permission_contracts.wrap_result("permission_group_created", group_id=group_id)

    return permission_operations.run_group_management_action(ctx, create_group)


def update_permission_group_result(ctx, service, group_id: int, data) -> dict:
    def update_group():
        payload = permission_payloads.build_update_group_payload(data)
        current = permission_access.get_manageable_group(ctx, service, group_id)
        merged = permission_payloads.merge_group_scope_payload(current, payload)
        permission_access.validate_group_scope(
            ctx,
            accessible_kbs=merged.get("accessible_kbs"),
            accessible_kb_nodes=merged.get("accessible_kb_nodes"),
            accessible_chats=merged.get("accessible_chats"),
        )
        require_group_update_result(service.update_group(group_id, payload))
        return permission_contracts.wrap_result("permission_group_updated")

    return permission_operations.run_group_management_action(ctx, update_group)


def delete_permission_group_result(ctx, service, group_id: int) -> dict:
    def delete_group():
        permission_access.get_manageable_group(ctx, service, group_id)
        require_group_delete_result(service.delete_group(group_id))
        return permission_contracts.wrap_result("permission_group_deleted")

    return permission_operations.run_group_management_action(ctx, delete_group)

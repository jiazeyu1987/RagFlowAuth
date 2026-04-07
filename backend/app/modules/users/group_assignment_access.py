from __future__ import annotations

from fastapi import HTTPException

from backend.app.core.permission_resolver import assert_group_tool_scope_within_snapshot
from backend.app.modules.permission_groups.service import PermissionGroupsService
from backend.app.modules.users.management_access import (
    assert_knowledge_management_access,
    chat_management_manager,
    knowledge_management_manager,
)
from backend.models.user import UserUpdate

SUB_ADMIN_GROUP_ASSIGNABLE_FIELDS = frozenset({"group_id", "group_ids"})


def _run_permission_group_id_validation(manager, *, ctx, group_ids: list[int]) -> None:
    try:
        manager.validate_permission_group_ids(
            user=ctx.user,
            group_ids=group_ids,
            permission_group_store=ctx.deps.permission_group_store,
        )
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc


def normalize_requested_group_ids(user_data: UserUpdate) -> list[int] | None:
    target_group_ids = user_data.group_ids
    if target_group_ids is None and user_data.group_id is not None:
        target_group_ids = [user_data.group_id]
    if target_group_ids is None:
        return None
    return [int(group_id) for group_id in target_group_ids]


def assert_sub_admin_group_assignment_only(ctx, user_data: UserUpdate) -> None:
    fields_set = set(getattr(user_data, "model_fields_set", set()) or set())
    disallowed = [field for field in fields_set if field not in SUB_ADMIN_GROUP_ASSIGNABLE_FIELDS]
    if not disallowed:
        return

    assert_knowledge_management_access(ctx)
    raise HTTPException(status_code=403, detail="sub_admin_group_assignment_only")


def validate_permission_group_tool_scope(ctx, *, group_ids: list[int]) -> None:
    if ctx.snapshot.is_admin:
        return
    store = getattr(ctx.deps, "permission_group_store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="permission_group_store_unavailable")
    for group_id in group_ids:
        group = store.get_group(group_id)
        if not group:
            raise HTTPException(status_code=400, detail=f"permission_group_not_found:{group_id}")
        assert_group_tool_scope_within_snapshot(ctx.snapshot, group)


def validate_sub_admin_assignable_group_ids(ctx, *, group_ids: list[int]) -> None:
    if not group_ids:
        return

    permission_group_service = PermissionGroupsService(ctx.deps)
    try:
        permission_group_service.validate_group_ids_manageable(
            user=ctx.user,
            group_ids=group_ids,
        )
    except HTTPException:
        raise

    manager = knowledge_management_manager(ctx)
    _run_permission_group_id_validation(manager, ctx=ctx, group_ids=group_ids)

    chat_manager = chat_management_manager(ctx)
    _run_permission_group_id_validation(chat_manager, ctx=ctx, group_ids=group_ids)

    validate_permission_group_tool_scope(ctx, group_ids=group_ids)

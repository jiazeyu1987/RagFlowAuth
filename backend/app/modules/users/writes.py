from __future__ import annotations

from backend.app.modules.users.access import (
    assert_sub_admin_group_assignment_only,
    assert_manageable_target_user,
    normalize_requested_group_ids,
    normalize_requested_tool_ids,
    validate_sub_admin_assignable_tool_ids,
    validate_sub_admin_assignable_group_ids,
)
from backend.app.modules.users.contracts import run_result_action, wrap_user_action


def create_user_result(*, service, user_data, created_by: str):
    return wrap_user_action(
        service.create_user,
        user_data=user_data,
        created_by=created_by,
    )

def _validate_assignable_group_ids(ctx, user_data) -> None:
    target_group_ids = normalize_requested_group_ids(user_data)
    if target_group_ids is None:
        return
    validate_sub_admin_assignable_group_ids(ctx, group_ids=target_group_ids)


def _validate_assignable_tool_ids(ctx, user_data) -> None:
    target_tool_ids = normalize_requested_tool_ids(user_data)
    if target_tool_ids is None:
        return
    validate_sub_admin_assignable_tool_ids(ctx, tool_ids=target_tool_ids)


def _validate_update_user_request(ctx, user_store, user_id: str, user_data) -> None:
    if ctx.snapshot.is_admin:
        return
    assert_sub_admin_group_assignment_only(ctx, user_data)
    assert_manageable_target_user(ctx, user_store, user_id)
    _validate_assignable_group_ids(ctx, user_data)
    _validate_assignable_tool_ids(ctx, user_data)


def update_user_result(*, ctx, user_store, service, user_id: str, user_data):
    _validate_update_user_request(ctx, user_store, user_id, user_data)
    return wrap_user_action(
        service.update_user,
        user_id=user_id,
        user_data=user_data,
        updated_by=str(getattr(ctx.user, "user_id", "") or "").strip() or None,
    )


def delete_user_result(*, service, user_id: str):
    return run_result_action(
        service.delete_user,
        user_id=user_id,
        message="user_deleted",
    )

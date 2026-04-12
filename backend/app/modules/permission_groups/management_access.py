from __future__ import annotations

from fastapi import HTTPException

from backend.app.modules.permission_groups.contracts import (
    require_knowledge_tree,
    require_object_list,
    require_object_payload,
)
from backend.app.modules.permission_groups.service import PermissionGroupsService


def knowledge_management_manager(
    ctx,
    *,
    status_code: int = 500,
    detail: str = "knowledge_management_manager_unavailable",
):
    manager = getattr(ctx.deps, "knowledge_management_manager", None)
    if manager is None:
        raise HTTPException(status_code=status_code, detail=detail)
    return manager


def chat_management_manager(ctx):
    manager = getattr(ctx.deps, "chat_management_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="chat_management_manager_unavailable")
    return manager


def assert_group_management(ctx) -> None:
    if str(getattr(ctx.user, "role", "") or "").strip().lower() != "sub_admin":
        raise HTTPException(status_code=403, detail="sub_admin_only_permission_group_management")
    manager = knowledge_management_manager(
        ctx,
        status_code=403,
        detail="sub_admin_only_permission_group_management",
    )
    try:
        manager.assert_can_manage(ctx.user)
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc


def validate_group_scope(ctx, *, accessible_kbs, accessible_kb_nodes, accessible_chats) -> None:
    if not _has_scope_entries(accessible_kbs, accessible_kb_nodes, accessible_chats):
        return
    try:
        knowledge_management_manager(ctx).validate_group_kb_scope(
            user=ctx.user,
            accessible_kbs=accessible_kbs,
            accessible_kb_nodes=accessible_kb_nodes,
        )
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc


def _has_scope_entries(*collections) -> bool:
    for values in collections:
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value.strip():
                return True
    return False
    try:
        chat_management_manager(ctx).validate_group_chat_scope(
            user=ctx.user,
            accessible_chats=accessible_chats,
        )
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc


def list_manageable_groups(ctx, service: PermissionGroupsService) -> list[dict]:
    groups = require_object_list(service.list_groups(), detail="permission_group_list_invalid_payload")
    groups = service.filter_manageable_groups(user=ctx.user, groups=groups)
    groups = require_object_list(groups, detail="permission_group_list_invalid_payload")
    groups = knowledge_management_manager(ctx).filter_manageable_permission_groups(user=ctx.user, groups=groups)
    groups = require_object_list(groups, detail="permission_group_list_invalid_payload")
    groups = chat_management_manager(ctx).filter_manageable_permission_groups(user=ctx.user, groups=groups)
    return require_object_list(groups, detail="permission_group_list_invalid_payload")


def list_assignable_groups(ctx, service: PermissionGroupsService) -> list[dict]:
    if ctx.snapshot.is_admin:
        return require_object_list(service.list_groups(), detail="permission_group_list_invalid_payload")
    assert_group_management(ctx)
    return list_manageable_groups(ctx, service)


def get_manageable_group(ctx, service: PermissionGroupsService, group_id: int) -> dict:
    group = service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="permission_group_not_found")
    group = require_object_payload(group, detail="permission_group_invalid_payload")
    group = service.assert_group_manageable(user=ctx.user, group=group)
    group = require_object_payload(group, detail="permission_group_invalid_payload")
    try:
        group = knowledge_management_manager(ctx).assert_permission_group_manageable(
            user=ctx.user,
            group=group,
        )
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc
    try:
        group = chat_management_manager(ctx).assert_permission_group_manageable(
            user=ctx.user,
            group=group,
        )
        return require_object_payload(group, detail="permission_group_invalid_payload")
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc


def list_manageable_knowledge_bases(ctx) -> list[dict]:
    kb_list = knowledge_management_manager(ctx).list_manageable_datasets(ctx.user)
    return require_object_list(kb_list, detail="permission_group_knowledge_bases_invalid_payload")


def get_manageable_knowledge_tree(ctx) -> dict:
    tree_data = knowledge_management_manager(ctx).list_visible_tree(ctx.user)
    return require_knowledge_tree(tree_data, detail="permission_group_knowledge_tree_invalid_payload")


def list_manageable_chat_resources(ctx) -> list[dict]:
    chat_list = chat_management_manager(ctx).list_manageable_chat_resources(ctx.user)
    return require_object_list(chat_list, detail="permission_group_chats_invalid_payload")

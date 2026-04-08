from __future__ import annotations

from typing import Any, TYPE_CHECKING

from backend.app.core.permission_legacy import resolve_group_permission_flags
from backend.app.core.permission_models import PermissionAccumulator, ResourceScope

if TYPE_CHECKING:
    from backend.app.dependencies import AppDependencies


def _safe_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []


def _normalize_tool_ids(raw: Any) -> frozenset[str]:
    tool_ids: set[str] = set()
    for item in _safe_list(raw):
        if not isinstance(item, str):
            continue
        value = item.strip()
        if value:
            tool_ids.add(value)
    return frozenset(tool_ids)


def _add_kb_ref(kb_names: set[str], ref: str, dataset_index: dict[str, dict[str, str]] | None) -> None:
    kb_names.add(ref)
    if not dataset_index:
        return
    by_id = dataset_index.get("by_id", {})
    by_name = dataset_index.get("by_name", {})
    if ref in by_id:
        kb_names.add(by_id[ref])
    elif ref in by_name:
        kb_names.add(by_name[ref])


def resolve_group_tool_scope(group: Any) -> tuple[ResourceScope, frozenset[str]]:
    flags = resolve_group_permission_flags(group)
    if not flags.can_view_tools:
        return ResourceScope.NONE, frozenset()
    tool_ids = _normalize_tool_ids(group.get("accessible_tools") if isinstance(group, dict) else None)
    if tool_ids:
        return ResourceScope.SET, tool_ids
    return ResourceScope.ALL, frozenset()


def apply_group_permissions(
    accumulator: PermissionAccumulator,
    *,
    group: dict[str, Any],
    dataset_index: dict[str, dict[str, str]] | None,
) -> None:
    flags = resolve_group_permission_flags(group)
    accumulator.can_upload = accumulator.can_upload or flags.can_upload
    accumulator.can_review = accumulator.can_review or flags.can_review
    accumulator.can_download = accumulator.can_download or flags.can_download
    accumulator.can_copy = accumulator.can_copy or flags.can_copy
    accumulator.can_delete = accumulator.can_delete or flags.can_delete
    accumulator.can_manage_kb_directory = accumulator.can_manage_kb_directory or flags.can_manage_kb_directory
    accumulator.can_view_kb_config = accumulator.can_view_kb_config or flags.can_view_kb_config
    accumulator.can_view_tools = accumulator.can_view_tools or flags.can_view_tools

    _apply_group_tool_scope(accumulator, group=group, can_view_tools=flags.can_view_tools)
    _apply_group_kb_scope(accumulator, group=group, dataset_index=dataset_index)
    _apply_group_chat_scope(accumulator, group=group)


def _apply_group_tool_scope(
    accumulator: PermissionAccumulator,
    *,
    group: dict[str, Any],
    can_view_tools: bool,
) -> None:
    if not can_view_tools:
        return
    group_tools = resolve_group_tool_scope(group)[1]
    if group_tools:
        accumulator.tool_has_scoped_access = True
        accumulator.tool_ids.update(group_tools)
        return
    accumulator.tool_has_global_access = True


def _apply_group_kb_scope(
    accumulator: PermissionAccumulator,
    *,
    group: dict[str, Any],
    dataset_index: dict[str, dict[str, str]] | None,
) -> None:
    for name in _safe_list(group.get("accessible_kbs")):
        if not isinstance(name, str):
            continue
        ref = name.strip()
        if not ref:
            continue
        if ref.startswith("node:"):
            node_id = ref[5:].strip()
            if node_id:
                accumulator.kb_node_ids.add(node_id)
            continue
        if ref.startswith("dataset:"):
            dataset_ref = ref[8:].strip()
            if dataset_ref:
                _add_kb_ref(accumulator.kb_names, dataset_ref, dataset_index)
            continue
        _add_kb_ref(accumulator.kb_names, ref, dataset_index)

    for node_id in _safe_list(group.get("accessible_kb_nodes")):
        if not isinstance(node_id, str):
            continue
        clean = node_id.strip()
        if clean:
            accumulator.kb_node_ids.add(clean)


def _apply_group_chat_scope(accumulator: PermissionAccumulator, *, group: dict[str, Any]) -> None:
    for chat_id in _safe_list(group.get("accessible_chats")):
        if isinstance(chat_id, str) and chat_id:
            accumulator.chat_ids.add(chat_id)


def expand_node_dataset_refs(
    deps: "AppDependencies",
    accumulator: PermissionAccumulator,
    *,
    dataset_index: dict[str, dict[str, str]] | None,
) -> None:
    if not accumulator.kb_node_ids:
        return
    manager = getattr(deps, "knowledge_directory_manager", None)
    if manager is None:
        return
    for dataset_id in manager.resolve_dataset_ids_from_nodes(accumulator.kb_node_ids):
        _add_kb_ref(accumulator.kb_names, dataset_id, dataset_index)


def apply_sub_admin_scope(
    deps: "AppDependencies",
    user: Any,
    accumulator: PermissionAccumulator,
    *,
    dataset_index: dict[str, dict[str, str]] | None,
) -> None:
    _apply_sub_admin_kb_scope(
        deps,
        user,
        accumulator,
        dataset_index=dataset_index,
    )
    _apply_sub_admin_chat_scope(deps, user, accumulator)


def _apply_sub_admin_kb_scope(
    deps: "AppDependencies",
    user: Any,
    accumulator: PermissionAccumulator,
    *,
    dataset_index: dict[str, dict[str, str]] | None,
) -> None:
    management_manager = getattr(deps, "knowledge_management_manager", None)
    if management_manager is None:
        return
    scope = management_manager.get_management_scope(user)
    if scope is None or not getattr(scope, "can_manage", False):
        return
    accumulator.can_upload = True
    accumulator.can_delete = True
    accumulator.can_manage_kb_directory = True
    accumulator.can_view_kb_config = True
    for dataset_id in getattr(scope, "dataset_ids", frozenset()) or frozenset():
        if isinstance(dataset_id, str) and dataset_id:
            _add_kb_ref(accumulator.kb_names, dataset_id, dataset_index)


def _apply_sub_admin_chat_scope(
    deps: "AppDependencies",
    user: Any,
    accumulator: PermissionAccumulator,
) -> None:
    chat_management_manager = getattr(deps, "chat_management_manager", None)
    if chat_management_manager is None:
        return
    for chat_ref in chat_management_manager.list_auto_granted_chat_refs(user):
        if isinstance(chat_ref, str) and chat_ref:
            accumulator.chat_ids.add(chat_ref)


def resolve_tool_scope(accumulator: PermissionAccumulator) -> ResourceScope:
    if not accumulator.can_view_tools:
        return ResourceScope.NONE
    if accumulator.tool_has_global_access or not accumulator.tool_has_scoped_access:
        return ResourceScope.ALL
    return ResourceScope.SET

from __future__ import annotations

from typing import Any, Iterable, TYPE_CHECKING

from fastapi import HTTPException

from backend.app.core.permission_models import PermissionAccumulator, PermissionSnapshot, ResourceScope
from backend.app.core.permission_scopes import (
    apply_group_permissions as _apply_group_permissions_impl,
    apply_user_tool_scope as _apply_user_tool_scope_impl,
    apply_sub_admin_scope as _apply_sub_admin_scope_impl,
    expand_node_dataset_refs as _expand_node_dataset_refs_impl,
    resolve_group_tool_scope as _resolve_group_tool_scope_impl,
    resolve_tool_scope as _resolve_tool_scope_impl,
)

if TYPE_CHECKING:
    from backend.app.dependencies import AppDependencies


def _effective_group_ids(user: Any) -> list[int]:
    group_ids: list[int] = []
    if getattr(user, "group_ids", None):
        group_ids.extend([int(gid) for gid in user.group_ids if gid is not None])
    seen: set[int] = set()
    ordered: list[int] = []
    for gid in group_ids:
        if gid not in seen:
            seen.add(gid)
            ordered.append(gid)
    return ordered


def resolve_group_tool_scope(group: Any) -> tuple[ResourceScope, frozenset[str]]:
    return _resolve_group_tool_scope_impl(group)


def group_tool_scope_within_snapshot(snapshot: PermissionSnapshot, group: Any) -> bool:
    group_scope, group_tool_ids = resolve_group_tool_scope(group)
    if group_scope == ResourceScope.NONE:
        return True
    if snapshot.tool_scope == ResourceScope.ALL:
        return True
    if snapshot.tool_scope != ResourceScope.SET:
        return False
    if group_scope != ResourceScope.SET:
        return False
    return group_tool_ids.issubset(snapshot.tool_ids)


def assert_group_tool_scope_within_snapshot(
    snapshot: PermissionSnapshot,
    group: Any,
    *,
    detail: str = "tool_out_of_management_scope",
    status_code: int = 400,
) -> None:
    if not group_tool_scope_within_snapshot(snapshot, group):
        raise HTTPException(status_code=status_code, detail=detail)


def _admin_permission_snapshot() -> PermissionSnapshot:
    return PermissionSnapshot(
        is_admin=True,
        can_upload=True,
        can_review=True,
        can_download=True,
        can_copy=True,
        can_delete=True,
        can_manage_kb_directory=True,
        can_view_kb_config=True,
        can_view_tools=True,
        kb_scope=ResourceScope.ALL,
        kb_names=frozenset(),
        chat_scope=ResourceScope.ALL,
        chat_ids=frozenset(),
        tool_scope=ResourceScope.ALL,
        tool_ids=frozenset(),
        can_manage_users=True,
    )


def _resolve_dataset_index(deps: "AppDependencies") -> dict[str, dict[str, str]] | None:
    ragflow_service = getattr(deps, "ragflow_service", None)
    if ragflow_service is None:
        return None
    get_index = getattr(ragflow_service, "get_dataset_index", None)
    if not callable(get_index):
        return None
    return get_index()


def _resolve_user_tool_ids(deps: "AppDependencies", user: Any) -> list[str]:
    store = getattr(deps, "user_tool_permission_store", None)
    if store is None:
        raise RuntimeError("user_tool_permission_store_unavailable")
    user_id = str(getattr(user, "user_id", "") or "").strip()
    if not user_id:
        return []
    return list(store.list_tool_ids(user_id))


def _iter_permission_groups(deps: "AppDependencies", user: Any) -> Iterable[dict[str, Any]]:
    for group_id in _effective_group_ids(user):
        group = deps.permission_group_store.get_group(group_id)
        if not group:
            continue
        yield group


def _apply_group_permissions(
    accumulator: PermissionAccumulator,
    *,
    group: dict[str, Any],
    dataset_index: dict[str, dict[str, str]] | None,
) -> None:
    _apply_group_permissions_impl(
        accumulator,
        group=group,
        dataset_index=dataset_index,
    )


def _expand_node_dataset_refs(
    deps: "AppDependencies",
    accumulator: PermissionAccumulator,
    *,
    dataset_index: dict[str, dict[str, str]] | None,
) -> None:
    _expand_node_dataset_refs_impl(
        deps,
        accumulator,
        dataset_index=dataset_index,
    )


def _apply_sub_admin_scope(
    deps: "AppDependencies",
    user: Any,
    accumulator: PermissionAccumulator,
    *,
    dataset_index: dict[str, dict[str, str]] | None,
) -> None:
    _apply_sub_admin_scope_impl(
        deps,
        user,
        accumulator,
        dataset_index=dataset_index,
    )


def _apply_user_tool_scope(
    accumulator: PermissionAccumulator,
    *,
    tool_ids: list[str],
) -> None:
    _apply_user_tool_scope_impl(accumulator, tool_ids=tool_ids)


def _resolve_tool_scope(accumulator: PermissionAccumulator) -> ResourceScope:
    return _resolve_tool_scope_impl(accumulator)


def _build_permission_snapshot(role: str, accumulator: PermissionAccumulator) -> PermissionSnapshot:
    return PermissionSnapshot(
        is_admin=False,
        can_upload=accumulator.can_upload,
        can_review=accumulator.can_review,
        can_download=accumulator.can_download,
        can_copy=accumulator.can_copy,
        can_delete=accumulator.can_delete,
        can_manage_kb_directory=accumulator.can_manage_kb_directory,
        can_view_kb_config=accumulator.can_view_kb_config,
        can_view_tools=accumulator.can_view_tools,
        kb_scope=ResourceScope.SET if accumulator.kb_names else ResourceScope.NONE,
        kb_names=frozenset(accumulator.kb_names),
        chat_scope=ResourceScope.SET if accumulator.chat_ids else ResourceScope.NONE,
        chat_ids=frozenset(accumulator.chat_ids),
        tool_scope=_resolve_tool_scope(accumulator),
        tool_ids=frozenset(accumulator.tool_ids),
        can_manage_users=role == "sub_admin" or accumulator.can_manage_users,
    )


def resolve_permissions(deps: "AppDependencies", user: Any) -> PermissionSnapshot:
    role = str(getattr(user, "role", "") or "")
    if role == "admin":
        return _admin_permission_snapshot()

    dataset_index = _resolve_dataset_index(deps)
    accumulator = PermissionAccumulator(can_manage_users=role == "sub_admin")

    for group in _iter_permission_groups(deps, user):
        _apply_group_permissions(accumulator, group=group, dataset_index=dataset_index)

    _expand_node_dataset_refs(deps, accumulator, dataset_index=dataset_index)

    if role == "sub_admin":
        _apply_sub_admin_scope(deps, user, accumulator, dataset_index=dataset_index)

    _apply_user_tool_scope(
        accumulator,
        tool_ids=_resolve_user_tool_ids(deps, user),
    )

    return _build_permission_snapshot(role, accumulator)


def filter_datasets_by_name(snapshot: PermissionSnapshot, datasets: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    if snapshot.kb_scope == ResourceScope.ALL:
        return list(datasets)
    if snapshot.kb_scope == ResourceScope.NONE:
        return []
    allowed = snapshot.kb_names
    filtered: list[dict[str, Any]] = []
    for ds in datasets:
        if not isinstance(ds, dict):
            continue
        if (ds.get("name") in allowed) or (ds.get("id") in allowed):
            filtered.append(ds)
    return filtered


def allowed_dataset_ids(snapshot: PermissionSnapshot, datasets: Iterable[dict[str, Any]]) -> list[str]:
    if snapshot.kb_scope == ResourceScope.NONE:
        return []
    permitted = datasets if snapshot.kb_scope == ResourceScope.ALL else filter_datasets_by_name(snapshot, datasets)
    ids: list[str] = []
    for ds in permitted:
        if not isinstance(ds, dict):
            continue
        ds_id = ds.get("id")
        if isinstance(ds_id, str) and ds_id:
            ids.append(ds_id)
    return ids


def assert_can_upload(snapshot: PermissionSnapshot) -> None:
    if not snapshot.can_upload:
        raise HTTPException(status_code=403, detail="no_upload_permission")


def assert_can_review(snapshot: PermissionSnapshot) -> None:
    if not snapshot.can_review:
        raise HTTPException(status_code=403, detail="no_review_permission")


def assert_can_download(snapshot: PermissionSnapshot) -> None:
    if not snapshot.can_download:
        raise HTTPException(status_code=403, detail="no_download_permission")


def assert_can_delete(snapshot: PermissionSnapshot) -> None:
    if not snapshot.can_delete:
        raise HTTPException(status_code=403, detail="no_delete_permission")


def assert_can_manage_kb_directory(snapshot: PermissionSnapshot) -> None:
    if not snapshot.can_manage_kb_directory:
        raise HTTPException(status_code=403, detail="no_kb_directory_manage_permission")


def assert_can_view_kb_config(snapshot: PermissionSnapshot) -> None:
    if not snapshot.can_view_kb_config:
        raise HTTPException(status_code=403, detail="no_kb_config_view_permission")


def assert_can_view_tools(snapshot: PermissionSnapshot) -> None:
    if not snapshot.can_view_tools:
        raise HTTPException(status_code=403, detail="no_tools_view_permission")


def assert_tool_allowed(snapshot: PermissionSnapshot, tool_id: str) -> None:
    assert_can_view_tools(snapshot)
    if snapshot.tool_scope == ResourceScope.ALL:
        return
    if snapshot.tool_scope == ResourceScope.NONE:
        raise HTTPException(status_code=403, detail="tool_not_allowed")
    clean_tool_id = str(tool_id or "").strip()
    if not clean_tool_id or clean_tool_id not in snapshot.tool_ids:
        raise HTTPException(status_code=403, detail="tool_not_allowed")


def assert_kb_allowed(snapshot: PermissionSnapshot, kb_name: str | Iterable[str]) -> None:
    if snapshot.kb_scope == ResourceScope.ALL:
        return
    if snapshot.kb_scope == ResourceScope.NONE:
        raise HTTPException(status_code=403, detail="kb_not_allowed")
    if isinstance(kb_name, str):
        candidates = {kb_name}
    else:
        candidates = {str(item).strip() for item in kb_name if str(item).strip()}
    if not candidates.intersection(snapshot.kb_names):
        raise HTTPException(status_code=403, detail="kb_not_allowed")


def normalize_accessible_chat_ids(chat_ids: Iterable[str]) -> set[str]:
    raw: set[str] = set()
    for cid in chat_ids:
        if cid.startswith("chat_"):
            raw.add(cid[5:])
        elif cid.startswith("agent_"):
            raw.add(cid[6:])
        else:
            raw.add(cid)
    return raw

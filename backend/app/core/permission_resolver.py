from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from fastapi import HTTPException

from backend.app.dependencies import AppDependencies


class ResourceScope(str, Enum):
    ALL = "ALL"
    SET = "SET"
    NONE = "NONE"


@dataclass(frozen=True)
class PermissionSnapshot:
    is_admin: bool
    can_upload: bool
    can_review: bool
    can_download: bool
    can_copy: bool
    can_delete: bool
    can_manage_kb_directory: bool
    can_view_kb_config: bool
    can_view_tools: bool
    kb_scope: ResourceScope
    kb_names: frozenset[str]
    chat_scope: ResourceScope
    chat_ids: frozenset[str]
    tool_scope: ResourceScope
    tool_ids: frozenset[str]

    def permissions_dict(self) -> dict[str, Any]:
        return {
            "can_upload": self.can_upload,
            "can_review": self.can_review,
            "can_download": self.can_download,
            "can_copy": self.can_copy,
            "can_delete": self.can_delete,
            "can_manage_kb_directory": self.can_manage_kb_directory,
            "can_view_kb_config": self.can_view_kb_config,
            "can_view_tools": self.can_view_tools,
            # Backward-compatible semantics:
            # - can_view_tools=false => no tools
            # - can_view_tools=true + accessible_tools=[] => all tools
            # - can_view_tools=true + accessible_tools=[...] => whitelisted tools
            "accessible_tools": sorted(self.tool_ids) if self.tool_scope == ResourceScope.SET else [],
        }


def _effective_group_ids(user: Any) -> list[int]:
    group_ids: list[int] = []
    if getattr(user, "group_ids", None):
        group_ids.extend([int(gid) for gid in user.group_ids if gid is not None])
    # Deduplicate while preserving order
    seen: set[int] = set()
    ordered: list[int] = []
    for gid in group_ids:
        if gid not in seen:
            seen.add(gid)
            ordered.append(gid)
    return ordered


def _safe_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []

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


def resolve_permissions(deps: AppDependencies, user: Any) -> PermissionSnapshot:
    is_admin = getattr(user, "role", None) == "admin"
    if is_admin:
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
        )

    can_upload = False
    can_review = False
    can_download = False
    can_copy = False
    can_delete = False
    can_manage_kb_directory = False
    can_view_kb_config = False
    can_view_tools = False
    kb_names: set[str] = set()
    kb_node_ids: set[str] = set()
    chat_ids: set[str] = set()
    tool_ids: set[str] = set()
    tool_has_global_access = False
    tool_has_scoped_access = False

    dataset_index: dict[str, dict[str, str]] | None = None
    ragflow_service = getattr(deps, "ragflow_service", None)
    if ragflow_service is not None:
        try:
            get_index = getattr(ragflow_service, "get_dataset_index", None)
            if callable(get_index):
                dataset_index = get_index()
        except Exception:
            dataset_index = None

    group_ids = _effective_group_ids(user)
    for group_id in group_ids:
        group = deps.permission_group_store.get_group(group_id)
        if not group:
            continue

        can_upload = can_upload or bool(group.get("can_upload", False))
        can_review = can_review or bool(group.get("can_review", False))
        can_download = can_download or bool(group.get("can_download", False))
        can_copy = can_copy or bool(group.get("can_copy", False))
        can_delete = can_delete or bool(group.get("can_delete", False))
        can_manage_kb_directory = can_manage_kb_directory or bool(group.get("can_manage_kb_directory", False))
        can_view_kb_config = can_view_kb_config or bool(group.get("can_view_kb_config", True))
        can_view_tools = can_view_tools or bool(group.get("can_view_tools", True))

        if bool(group.get("can_view_tools", True)):
            group_tools = _safe_list(group.get("accessible_tools"))
            if group_tools:
                tool_has_scoped_access = True
                for tid in group_tools:
                    if isinstance(tid, str):
                        value = tid.strip()
                        if value:
                            tool_ids.add(value)
            else:
                # Legacy groups without tool-level restriction keep full tools visibility.
                tool_has_global_access = True

        for name in _safe_list(group.get("accessible_kbs")):
            if isinstance(name, str) and name:
                ref = name.strip()
                if not ref:
                    continue
                if ref.startswith("node:"):
                    node_id = ref[5:].strip()
                    if node_id:
                        kb_node_ids.add(node_id)
                    continue
                if ref.startswith("dataset:"):
                    dataset_ref = ref[8:].strip()
                    if dataset_ref:
                        _add_kb_ref(kb_names, dataset_ref, dataset_index)
                    continue
                _add_kb_ref(kb_names, ref, dataset_index)
        for node_id in _safe_list(group.get("accessible_kb_nodes")):
            if isinstance(node_id, str):
                clean = node_id.strip()
                if clean:
                    kb_node_ids.add(clean)
        for cid in _safe_list(group.get("accessible_chats")):
            if isinstance(cid, str) and cid:
                chat_ids.add(cid)

    if kb_node_ids:
        manager = getattr(deps, "knowledge_directory_manager", None)
        if manager is not None:
            try:
                dataset_ids = manager.resolve_dataset_ids_from_nodes(kb_node_ids)
            except Exception:
                dataset_ids = []
            for dataset_id in dataset_ids:
                _add_kb_ref(kb_names, dataset_id, dataset_index)

    # NOTE:
    # 业务授权以“权限组（resolver）”为准，不再合并按用户单独授权的 KB/Chat 可见性。
    # Legacy per-user KB/chat grants are no longer supported and do not affect authorization.

    kb_scope = ResourceScope.SET if kb_names else ResourceScope.NONE
    chat_scope = ResourceScope.SET if chat_ids else ResourceScope.NONE
    if not can_view_tools:
        tool_scope = ResourceScope.NONE
    elif tool_has_global_access or not tool_has_scoped_access:
        tool_scope = ResourceScope.ALL
    else:
        tool_scope = ResourceScope.SET

    return PermissionSnapshot(
        is_admin=False,
        can_upload=can_upload,
        can_review=can_review,
        can_download=can_download,
        can_copy=can_copy,
        can_delete=can_delete,
        can_manage_kb_directory=can_manage_kb_directory,
        can_view_kb_config=can_view_kb_config,
        can_view_tools=can_view_tools,
        kb_scope=kb_scope,
        kb_names=frozenset(kb_names),
        chat_scope=chat_scope,
        chat_ids=frozenset(chat_ids),
        tool_scope=tool_scope,
        tool_ids=frozenset(tool_ids),
    )


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
    """
    Return the dataset ids the user can use for retrieval/search operations.

    Note: For non-admin users we rely on resolver-derived `kb_names`, which may
    include both dataset names and dataset ids (via dataset index expansion).
    """
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
    if snapshot.is_admin:
        return
    if not snapshot.can_upload:
        raise HTTPException(status_code=403, detail="no_upload_permission")


def assert_can_review(snapshot: PermissionSnapshot) -> None:
    if snapshot.is_admin:
        return
    if not snapshot.can_review:
        raise HTTPException(status_code=403, detail="no_review_permission")


def assert_can_download(snapshot: PermissionSnapshot) -> None:
    if snapshot.is_admin:
        return
    if not snapshot.can_download:
        raise HTTPException(status_code=403, detail="no_download_permission")


def assert_can_delete(snapshot: PermissionSnapshot) -> None:
    if snapshot.is_admin:
        return
    if not snapshot.can_delete:
        raise HTTPException(status_code=403, detail="no_delete_permission")


def assert_can_manage_kb_directory(snapshot: PermissionSnapshot) -> None:
    if snapshot.is_admin:
        return
    if not snapshot.can_manage_kb_directory:
        raise HTTPException(status_code=403, detail="no_kb_directory_manage_permission")


def assert_can_view_kb_config(snapshot: PermissionSnapshot) -> None:
    if snapshot.is_admin:
        return
    if not snapshot.can_view_kb_config:
        raise HTTPException(status_code=403, detail="no_kb_config_view_permission")


def assert_can_view_tools(snapshot: PermissionSnapshot) -> None:
    if snapshot.is_admin:
        return
    if not snapshot.can_view_tools:
        raise HTTPException(status_code=403, detail="no_tools_view_permission")


def assert_tool_allowed(snapshot: PermissionSnapshot, tool_id: str) -> None:
    if snapshot.is_admin:
        return
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
    """
    Permission groups store chat IDs as 'chat_<id>' / 'agent_<id>' strings.
    Normalize to raw IDs for filtering ragflow responses that use 'id'.
    """
    raw: set[str] = set()
    for cid in chat_ids:
        if cid.startswith("chat_"):
            raw.add(cid[5:])
        elif cid.startswith("agent_"):
            raw.add(cid[6:])
        else:
            raw.add(cid)
    return raw

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
    can_delete: bool
    kb_scope: ResourceScope
    kb_names: frozenset[str]
    chat_scope: ResourceScope
    chat_ids: frozenset[str]

    def permissions_dict(self) -> dict[str, bool]:
        return {
            "can_upload": self.can_upload,
            "can_review": self.can_review,
            "can_download": self.can_download,
            "can_delete": self.can_delete,
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
            can_delete=True,
            kb_scope=ResourceScope.ALL,
            kb_names=frozenset(),
            chat_scope=ResourceScope.ALL,
            chat_ids=frozenset(),
        )

    can_upload = False
    can_review = False
    can_download = False
    can_delete = False
    kb_names: set[str] = set()
    chat_ids: set[str] = set()

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
        can_delete = can_delete or bool(group.get("can_delete", False))

        for name in _safe_list(group.get("accessible_kbs")):
            if isinstance(name, str) and name:
                _add_kb_ref(kb_names, name, dataset_index)
        for cid in _safe_list(group.get("accessible_chats")):
            if isinstance(cid, str) and cid:
                chat_ids.add(cid)

    # NOTE:
    # 业务授权以“权限组（resolver）”为准，不再合并按用户单独授权的 KB/Chat 可见性。
    # user_kb_permissions / user_chat_permissions 保留为历史/管理用途，但不参与当前授权决策。

    kb_scope = ResourceScope.SET if kb_names else ResourceScope.NONE
    chat_scope = ResourceScope.SET if chat_ids else ResourceScope.NONE

    return PermissionSnapshot(
        is_admin=False,
        can_upload=can_upload,
        can_review=can_review,
        can_download=can_download,
        can_delete=can_delete,
        kb_scope=kb_scope,
        kb_names=frozenset(kb_names),
        chat_scope=chat_scope,
        chat_ids=frozenset(chat_ids),
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


def assert_kb_allowed(snapshot: PermissionSnapshot, kb_name: str) -> None:
    if snapshot.kb_scope == ResourceScope.ALL:
        return
    if snapshot.kb_scope == ResourceScope.NONE:
        raise HTTPException(status_code=403, detail="kb_not_allowed")
    if kb_name not in snapshot.kb_names:
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

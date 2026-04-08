from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.core.permdbg import permdbg
from backend.app.core.permission_resolver import ResourceScope
from backend.services.users.group_compat import normalize_legacy_group_ids


@dataclass(frozen=True)
class _AuthMeAccessSummary:
    accessible_kb_ids: tuple[str, ...]
    accessible_kb_names: tuple[str, ...]
    accessible_chats: tuple[str, ...]
    capabilities: dict[str, dict[str, dict[str, Any]]]


def _permission_group_ids(user: Any) -> list[Any]:
    return normalize_legacy_group_ids(
        group_ids=getattr(user, "group_ids", None),
        group_id=getattr(user, "group_id", None),
    )


def _build_permission_groups(*, deps: Any, user: Any) -> list[dict[str, Any]]:
    permission_groups_list: list[dict[str, Any]] = []
    for group_id in _permission_group_ids(user):
        group = deps.permission_group_store.get_group(group_id)
        if not group:
            continue
        permission_groups_list.append({"group_id": group_id, "group_name": group.get("group_name", "")})
    return permission_groups_list


def _resolve_accessible_kbs(*, deps: Any, snapshot: Any) -> tuple[set[str], set[str]]:
    if snapshot.kb_scope == ResourceScope.ALL:
        datasets = deps.ragflow_service.list_all_datasets() if hasattr(deps.ragflow_service, "list_all_datasets") else deps.ragflow_service.list_datasets()
        accessible_kb_ids_set: set[str] = {ds.get("id") for ds in datasets or [] if isinstance(ds, dict) and ds.get("id")}
        accessible_kb_names_set: set[str] = {ds.get("name") for ds in datasets or [] if isinstance(ds, dict) and ds.get("name")}
    else:
        accessible_kb_ids_set = set(deps.ragflow_service.normalize_dataset_ids(snapshot.kb_names)) if hasattr(deps.ragflow_service, "normalize_dataset_ids") else set()
        accessible_kb_names_set = set(deps.ragflow_service.resolve_dataset_names(snapshot.kb_names)) if hasattr(deps.ragflow_service, "resolve_dataset_names") else set(snapshot.kb_names)
    return accessible_kb_ids_set, accessible_kb_names_set


def _resolve_accessible_chats(*, deps: Any, snapshot: Any) -> set[str]:
    if snapshot.chat_scope == ResourceScope.ALL:
        return set(deps.ragflow_chat_service.list_all_chat_ids())
    return set(snapshot.chat_ids)


def _resolve_managed_kb_root_path(*, deps: Any, user: Any) -> str | None:
    management_manager = getattr(deps, "knowledge_management_manager", None)
    if management_manager is None:
        return None
    scope = management_manager.get_management_scope(user)
    return getattr(scope, "root_node_path", None)


def _group_kb_refs(*, deps: Any, user: Any) -> list[str]:
    refs: list[str] = []
    for group_id in _permission_group_ids(user):
        group = deps.permission_group_store.get_group(group_id)
        if not group:
            continue
        for ref in group.get("accessible_kbs") or []:
            if isinstance(ref, str) and ref:
                refs.append(ref)
    return refs


def _log_snapshot_debug(*, deps: Any, user: Any, snapshot: Any) -> None:
    permdbg(
        "auth.me.snapshot",
        user=user.username,
        role=user.role,
        group_ids=_permission_group_ids(user),
        kb_scope=snapshot.kb_scope,
        kb_refs=sorted(snapshot.kb_names)[:50],
        group_kbs=sorted(set(_group_kb_refs(deps=deps, user=user)))[:50],
    )


def _build_access_summary(*, deps: Any, snapshot: Any) -> _AuthMeAccessSummary:
    accessible_kb_ids_set, accessible_kb_names_set = _resolve_accessible_kbs(deps=deps, snapshot=snapshot)
    accessible_chats_set = _resolve_accessible_chats(deps=deps, snapshot=snapshot)
    capabilities = snapshot.capabilities_dict(
        accessible_kb_ids=accessible_kb_ids_set,
        accessible_chat_ids=accessible_chats_set,
    )
    return _AuthMeAccessSummary(
        accessible_kb_ids=tuple(sorted(accessible_kb_ids_set)),
        accessible_kb_names=tuple(sorted(accessible_kb_names_set)),
        accessible_chats=tuple(sorted(accessible_chats_set)),
        capabilities=capabilities,
    )


def _log_effective_access(summary: _AuthMeAccessSummary) -> None:
    permdbg(
        "auth.me.effective",
        accessible_kbs=list(summary.accessible_kb_names[:50]),
        accessible_kb_ids=list(summary.accessible_kb_ids[:50]),
        accessible_chats_count=len(summary.accessible_chats),
    )


def build_auth_me_payload(*, deps: Any, user: Any, snapshot: Any) -> dict[str, Any]:
    permissions = snapshot.permissions_dict()
    managed_kb_root_path = _resolve_managed_kb_root_path(deps=deps, user=user)
    _log_snapshot_debug(deps=deps, user=user, snapshot=snapshot)
    access_summary = _build_access_summary(deps=deps, snapshot=snapshot)
    _log_effective_access(access_summary)

    return {
        "user_id": user.user_id,
        "username": user.username,
        "full_name": getattr(user, "full_name", None),
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "group_id": user.group_id,
        "group_ids": user.group_ids,
        "permission_groups": _build_permission_groups(deps=deps, user=user),
        "scopes": [],
        "permissions": permissions,
        "capabilities": access_summary.capabilities,
        "max_login_sessions": int(getattr(user, "max_login_sessions", 3) or 3),
        "idle_timeout_minutes": int(getattr(user, "idle_timeout_minutes", 120) or 120),
        "can_change_password": bool(getattr(user, "can_change_password", True)),
        "disable_login_enabled": bool(getattr(user, "disable_login_enabled", False)),
        "disable_login_until_ms": (
            int(getattr(user, "disable_login_until_ms"))
            if getattr(user, "disable_login_until_ms", None) is not None
            else None
        ),
        "managed_kb_root_node_id": getattr(user, "managed_kb_root_node_id", None),
        "managed_kb_root_path": managed_kb_root_path,
        # Legacy field: dataset names (for display).
        "accessible_kbs": list(access_summary.accessible_kb_names),
        # New field: dataset ids (for API operations / stage-3 migration).
        "accessible_kb_ids": list(access_summary.accessible_kb_ids),
        "accessible_chats": list(access_summary.accessible_chats),
    }

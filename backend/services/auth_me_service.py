from __future__ import annotations

from typing import Any

from backend.app.core.permdbg import permdbg
from backend.app.core.permission_resolver import ResourceScope


def _build_permission_groups(*, deps: Any, user: Any) -> list[dict[str, Any]]:
    permission_groups_list: list[dict[str, Any]] = []
    group_ids = list(user.group_ids or [])
    if not group_ids and user.group_id is not None:
        group_ids = [user.group_id]

    for group_id in group_ids:
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


def build_auth_me_payload(*, deps: Any, user: Any, snapshot: Any) -> dict[str, Any]:
    permissions = snapshot.permissions_dict()

    # Debug: trace where KB visibility comes from (permission groups + per-user grants).
    try:
        group_ids = list(user.group_ids or [])
        group_kbs: list[str] = []
        for gid in group_ids:
            group = deps.permission_group_store.get_group(gid)
            if not group:
                continue
            for ref in (group.get("accessible_kbs") or []):
                if isinstance(ref, str) and ref:
                    group_kbs.append(ref)
        permdbg(
            "auth.me.snapshot",
            user=user.username,
            role=user.role,
            group_ids=group_ids,
            kb_scope=snapshot.kb_scope,
            kb_refs=sorted(list(snapshot.kb_names))[:50],
            group_kbs=sorted(set([x for x in group_kbs if isinstance(x, str) and x]))[:50],
        )
    except Exception:
        # Best-effort debug only.
        pass

    accessible_kb_ids_set, accessible_kb_names_set = _resolve_accessible_kbs(deps=deps, snapshot=snapshot)
    accessible_chats_set = _resolve_accessible_chats(deps=deps, snapshot=snapshot)

    try:
        permdbg(
            "auth.me.effective",
            accessible_kbs=sorted(accessible_kb_names_set)[:50],
            accessible_kb_ids=sorted(accessible_kb_ids_set)[:50],
            accessible_chats_count=len(accessible_chats_set),
        )
    except Exception:
        pass

    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "group_id": user.group_id,
        "group_ids": user.group_ids,
        "permission_groups": _build_permission_groups(deps=deps, user=user),
        "scopes": [],
        "permissions": permissions,
        "max_login_sessions": int(getattr(user, "max_login_sessions", 3) or 3),
        "idle_timeout_minutes": int(getattr(user, "idle_timeout_minutes", 120) or 120),
        "can_change_password": bool(getattr(user, "can_change_password", True)),
        "disable_login_enabled": bool(getattr(user, "disable_login_enabled", False)),
        "disable_login_until_ms": (
            int(getattr(user, "disable_login_until_ms"))
            if getattr(user, "disable_login_until_ms", None) is not None
            else None
        ),
        # Legacy field: dataset names (for display).
        "accessible_kbs": sorted(accessible_kb_names_set),
        # New field: dataset ids (for API operations / stage-3 migration).
        "accessible_kb_ids": sorted(accessible_kb_ids_set),
        "accessible_chats": sorted(accessible_chats_set),
    }

from __future__ import annotations

from fastapi import HTTPException

from backend.app.modules.permission_groups.contracts import (
    require_folder_snapshot,
    visible_folder_ids,
)
from backend.app.modules.permission_groups.management_access import list_manageable_groups
from backend.app.modules.permission_groups.service import PermissionGroupsService


def list_manageable_folder_snapshot(ctx, service: PermissionGroupsService) -> dict:
    groups = list_manageable_groups(ctx, service)
    snapshot = require_folder_snapshot(
        service.list_group_folders(),
        detail="permission_group_folder_snapshot_invalid_payload",
    )
    clean_user_id = str(getattr(ctx.user, "user_id", "") or "").strip()
    folders = list(snapshot.get("folders", []))
    by_id = {
        str(folder.get("id")): folder
        for folder in folders
        if isinstance(folder.get("id"), str) and folder.get("id")
    }
    visible_ids: set[str] = set()
    group_bindings: dict[str, str | None] = {}
    root_group_count = 0

    def include_with_ancestors(folder_id: str | None) -> None:
        current_id = str(folder_id or "").strip()
        guard: set[str] = set()
        while current_id and current_id not in guard:
            guard.add(current_id)
            visible_ids.add(current_id)
            parent_id = by_id.get(current_id, {}).get("parent_id")
            current_id = str(parent_id).strip() if isinstance(parent_id, str) and parent_id.strip() else ""

    for group in groups:
        if not isinstance(group, dict):
            continue
        group_id = group.get("group_id")
        if not isinstance(group_id, int):
            continue
        clean_folder_id = str(group.get("folder_id") or "").strip() or None
        group_bindings[str(group_id)] = clean_folder_id
        if clean_folder_id is None:
            root_group_count += 1
        include_with_ancestors(clean_folder_id)
    for folder in folders:
        if str(folder.get("created_by") or "").strip() == clean_user_id:
            include_with_ancestors(folder.get("id"))

    return {
        **snapshot,
        "folders": [folder for folder in folders if str(folder.get("id") or "") in visible_ids],
        "group_bindings": group_bindings,
        "root_group_count": root_group_count,
    }


def get_visible_folder_scope(ctx, service: PermissionGroupsService) -> tuple[dict, set[str]]:
    folder_snapshot = list_manageable_folder_snapshot(ctx, service)
    return folder_snapshot, visible_folder_ids(folder_snapshot)


def assert_folder_visible(folder_id: str, visible_ids: set[str]) -> None:
    if folder_id not in visible_ids:
        raise HTTPException(status_code=403, detail="permission_group_folder_out_of_management_scope")


def validate_folder_parent(parent_id: str | None, visible_ids: set[str]) -> None:
    if parent_id and parent_id not in visible_ids:
        raise HTTPException(status_code=403, detail="permission_group_folder_out_of_management_scope")


def build_group_folder_update_payload(data, *, visible_ids: set[str]) -> dict[str, object | None]:
    fields_set = set(getattr(data, "model_fields_set", set()) or set())
    if not fields_set:
        raise HTTPException(status_code=400, detail="missing_updates")

    payload: dict[str, object | None] = {}
    if "name" in fields_set:
        payload["name"] = data.name
    if "parent_id" in fields_set:
        validate_folder_parent(data.parent_id, visible_ids)
        payload["parent_id"] = data.parent_id
    return payload

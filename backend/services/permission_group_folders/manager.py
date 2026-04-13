from __future__ import annotations

from typing import Any

from .store import PermissionGroupFolderStore


class PermissionGroupFolderManager:
    def __init__(self, store: PermissionGroupFolderStore):
        self._store = store

    def snapshot(self, groups: list[dict[str, Any]]) -> dict[str, Any]:
        folders = self._store.list_folders()
        folder_by_id = {
            str(folder.get("folder_id")): folder
            for folder in folders
            if isinstance(folder, dict) and isinstance(folder.get("folder_id"), str) and folder.get("folder_id")
        }

        path_cache: dict[str, str] = {}

        def folder_path(folder_id: str | None) -> str:
            if not folder_id:
                return "/"
            if folder_id in path_cache:
                return path_cache[folder_id]
            parts: list[str] = []
            guard: set[str] = set()
            cur_id = folder_id
            while cur_id and cur_id not in guard:
                guard.add(cur_id)
                folder = folder_by_id.get(cur_id)
                if not folder:
                    break
                name = str(folder.get("name") or "").strip()
                if name:
                    parts.append(name)
                parent = folder.get("parent_id")
                cur_id = str(parent) if isinstance(parent, str) and parent else None
            path = "/" + "/".join(reversed(parts)) if parts else "/"
            path_cache[folder_id] = path
            return path

        group_bindings: dict[int, str | None] = {}
        group_counts: dict[str, int] = {}
        for group in groups or []:
            if not isinstance(group, dict):
                continue
            group_id = group.get("group_id")
            if not isinstance(group_id, int):
                continue
            folder_id = group.get("folder_id")
            clean_folder_id = str(folder_id) if isinstance(folder_id, str) and folder_id else None
            group_bindings[group_id] = clean_folder_id
            key = clean_folder_id or "__root__"
            group_counts[key] = int(group_counts.get(key, 0) or 0) + 1

        out_folders = []
        for folder in folders:
            folder_id = str(folder.get("folder_id") or "")
            if not folder_id:
                continue
            out_folders.append(
                {
                    "id": folder_id,
                    "name": str(folder.get("name") or ""),
                    "parent_id": folder.get("parent_id"),
                    "path": folder_path(folder_id),
                    "created_by": folder.get("created_by"),
                    "created_at_ms": folder.get("created_at_ms"),
                    "updated_at_ms": folder.get("updated_at_ms"),
                    "group_count": int(group_counts.get(folder_id, 0) or 0),
                }
            )

        return {
            "folders": out_folders,
            "group_bindings": {str(k): v for k, v in group_bindings.items()},
            "root_group_count": int(group_counts.get("__root__", 0) or 0),
        }

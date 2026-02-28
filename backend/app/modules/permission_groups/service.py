from __future__ import annotations

from typing import Any

from backend.app.dependencies import AppDependencies

from backend.app.modules.permission_groups.repo import PermissionGroupsRepo


class PermissionGroupsService:
    def __init__(self, deps: AppDependencies):
        self._repo = PermissionGroupsRepo(deps)

    def list_groups(self) -> list[dict[str, Any]]:
        return self._repo.list_groups()

    def get_group(self, group_id: int) -> dict[str, Any] | None:
        return self._repo.get_group(group_id)

    def create_group(self, payload: dict[str, Any]) -> int | None:
        return self._repo.create_group(payload)

    def update_group(self, group_id: int, payload: dict[str, Any]) -> bool:
        return self._repo.update_group(group_id, payload)

    def delete_group(self, group_id: int) -> bool:
        return self._repo.delete_group(group_id)

    def list_knowledge_bases(self) -> list[dict[str, str]]:
        return self._repo.list_knowledge_bases()

    def list_knowledge_tree(self) -> dict[str, Any]:
        return self._repo.list_knowledge_tree()

    def list_chat_agents(self) -> list[dict[str, str]]:
        return self._repo.list_chat_agents()

    def list_group_folders(self) -> dict[str, Any]:
        return self._repo.list_group_folders()

    def create_group_folder(self, name: str, parent_id: str | None, *, created_by: str | None) -> dict[str, Any]:
        return self._repo.create_group_folder(name=name, parent_id=parent_id, created_by=created_by)

    def update_group_folder(self, folder_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._repo.update_group_folder(folder_id, payload)

    def delete_group_folder(self, folder_id: str) -> bool:
        return self._repo.delete_group_folder(folder_id)

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from backend.app.dependencies import AppDependencies

from backend.app.modules.permission_groups.repo import PermissionGroupsRepo
from backend.services.permission_groups.manager import PermissionManagementError, PermissionManagementManager


class PermissionGroupsService:
    def __init__(self, deps: AppDependencies):
        self._repo = PermissionGroupsRepo(deps)
        self._manager = PermissionManagementManager(self._repo)

    @staticmethod
    def _raise(err: PermissionManagementError) -> None:
        raise HTTPException(status_code=err.status_code, detail=err.code) from err

    def list_groups(self) -> list[dict[str, Any]]:
        try:
            return self._manager.list_groups()
        except PermissionManagementError as e:
            self._raise(e)

    def get_group(self, group_id: int) -> dict[str, Any] | None:
        try:
            return self._manager.get_group(group_id)
        except PermissionManagementError as e:
            self._raise(e)

    def create_group(self, payload: dict[str, Any]) -> int | None:
        try:
            return self._manager.create_group(payload)
        except PermissionManagementError as e:
            self._raise(e)

    def update_group(self, group_id: int, payload: dict[str, Any]) -> bool:
        try:
            self._manager.update_group(group_id, payload)
            return True
        except PermissionManagementError as e:
            self._raise(e)

    def delete_group(self, group_id: int) -> bool:
        try:
            self._manager.delete_group(group_id)
            return True
        except PermissionManagementError as e:
            self._raise(e)

    def list_knowledge_bases(self) -> list[dict[str, str]]:
        try:
            return self._manager.list_knowledge_bases()
        except PermissionManagementError as e:
            self._raise(e)

    def list_knowledge_tree(self) -> dict[str, Any]:
        try:
            return self._manager.list_knowledge_tree()
        except PermissionManagementError as e:
            self._raise(e)

    def list_chat_agents(self) -> list[dict[str, str]]:
        try:
            return self._manager.list_chat_agents()
        except PermissionManagementError as e:
            self._raise(e)

    def list_group_folders(self) -> dict[str, Any]:
        try:
            return self._manager.list_group_folders()
        except PermissionManagementError as e:
            self._raise(e)

    def create_group_folder(self, name: str, parent_id: str | None, *, created_by: str | None) -> dict[str, Any]:
        try:
            return self._manager.create_group_folder(name=name, parent_id=parent_id, created_by=created_by)
        except PermissionManagementError as e:
            self._raise(e)

    def update_group_folder(self, folder_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._manager.update_group_folder(folder_id, payload)
        except PermissionManagementError as e:
            self._raise(e)

    def delete_group_folder(self, folder_id: str) -> bool:
        try:
            self._manager.delete_group_folder(folder_id)
            return True
        except PermissionManagementError as e:
            self._raise(e)

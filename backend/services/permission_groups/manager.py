from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class PermissionGroupsPort(Protocol):
    def list_groups(self) -> list[dict[str, Any]]: ...
    def get_group(self, group_id: int) -> dict[str, Any] | None: ...
    def create_group(self, payload: dict[str, Any]) -> int | None: ...
    def update_group(self, group_id: int, payload: dict[str, Any]) -> bool: ...
    def delete_group(self, group_id: int) -> bool: ...
    def list_knowledge_bases(self) -> list[dict[str, str]]: ...
    def list_knowledge_tree(self) -> dict[str, Any]: ...
    def list_chat_agents(self) -> list[dict[str, str]]: ...
    def list_group_folders(self) -> dict[str, Any]: ...
    def create_group_folder(self, name: str, parent_id: str | None, *, created_by: str | None) -> dict[str, Any]: ...
    def update_group_folder(self, folder_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    def delete_group_folder(self, folder_id: str) -> bool: ...


@dataclass
class PermissionManagementError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class PermissionManagementManager:
    """
    Reusable permission-management domain manager.

    It depends only on PermissionGroupsPort, so it can be reused in other
    backends by swapping repository adapters.
    """

    def __init__(self, port: PermissionGroupsPort):
        self._port = port

    def list_groups(self) -> list[dict[str, Any]]:
        return self._port.list_groups()

    def get_group(self, group_id: int) -> dict[str, Any] | None:
        return self._port.get_group(group_id)

    def create_group(self, payload: dict[str, Any]) -> int:
        try:
            group_id = self._port.create_group(payload)
        except ValueError as e:
            raise PermissionManagementError(str(e), status_code=400) from e
        if not group_id:
            raise PermissionManagementError("create_group_failed", status_code=400)
        return int(group_id)

    def update_group(self, group_id: int, payload: dict[str, Any]) -> None:
        try:
            ok = self._port.update_group(group_id, payload)
        except ValueError as e:
            raise PermissionManagementError(str(e), status_code=400) from e
        if not ok:
            raise PermissionManagementError("update_group_failed", status_code=400)

    def delete_group(self, group_id: int) -> None:
        ok = self._port.delete_group(group_id)
        if not ok:
            raise PermissionManagementError("delete_group_failed", status_code=400)

    def list_knowledge_bases(self) -> list[dict[str, str]]:
        return self._port.list_knowledge_bases()

    def list_knowledge_tree(self) -> dict[str, Any]:
        return self._port.list_knowledge_tree()

    def list_chat_agents(self) -> list[dict[str, str]]:
        return self._port.list_chat_agents()

    def list_group_folders(self) -> dict[str, Any]:
        return self._port.list_group_folders()

    def create_group_folder(self, name: str, parent_id: str | None, *, created_by: str | None) -> dict[str, Any]:
        try:
            return self._port.create_group_folder(name=name, parent_id=parent_id, created_by=created_by)
        except ValueError as e:
            raise PermissionManagementError(str(e), status_code=400) from e

    def update_group_folder(self, folder_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._port.update_group_folder(folder_id, payload)
        except ValueError as e:
            code = str(e)
            status = 404 if code == "folder_not_found" else 400
            raise PermissionManagementError(code, status_code=status) from e

    def delete_group_folder(self, folder_id: str) -> None:
        try:
            ok = self._port.delete_group_folder(folder_id)
        except ValueError as e:
            code = str(e)
            status = 404 if code == "folder_not_found" else 400
            raise PermissionManagementError(code, status_code=status) from e
        if not ok:
            raise PermissionManagementError("folder_not_found", status_code=404)

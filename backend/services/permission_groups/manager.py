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
    def list_group_folders(self, groups: list[dict[str, Any]] | None = None) -> dict[str, Any]: ...
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

    def list_group_folders(self, groups: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return self._port.list_group_folders(groups)

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

    def assert_group_manageable(self, *, user: Any, group: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(group, dict):
            raise PermissionManagementError("permission_group_not_found", status_code=404)
        role = self._role(user)
        if role == "admin":
            return group
        if role != "sub_admin":
            raise PermissionManagementError("sub_admin_only_permission_group_management", status_code=403)
        if str(group.get("created_by") or "").strip() != self._user_id(user):
            raise PermissionManagementError("permission_group_out_of_management_scope", status_code=403)
        return group

    def filter_manageable_groups(self, *, user: Any, groups: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        manageable: list[dict[str, Any]] = []
        for group in groups or []:
            try:
                manageable.append(self.assert_group_manageable(user=user, group=group))
            except PermissionManagementError:
                continue
        return manageable

    def validate_group_ids_manageable(self, *, user: Any, group_ids: list[int]) -> None:
        for raw_group_id in group_ids:
            group_id = int(raw_group_id)
            group = self._port.get_group(group_id)
            if not group:
                raise PermissionManagementError(f"permission_group_not_found:{group_id}", status_code=400)
            self.assert_group_manageable(user=user, group=group)

    @staticmethod
    def _role(user: Any) -> str:
        return str(getattr(user, "role", "") or "").strip().lower()

    @staticmethod
    def _user_id(user: Any) -> str:
        user_id = str(getattr(user, "user_id", "") or "").strip()
        if not user_id:
            raise PermissionManagementError("permission_group_owner_required", status_code=500)
        return user_id

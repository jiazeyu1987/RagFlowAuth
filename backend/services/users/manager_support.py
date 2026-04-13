from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from backend.app.core.tool_catalog import normalize_assignable_tool_ids


@dataclass(frozen=True)
class UserOrganizationContext:
    company_id: int | None
    department_id: int | None
    department: Any


@dataclass(frozen=True)
class UserAccessAssignment:
    manager_user_id: str | None
    managed_kb_root_node_id: str | None


class UserManagementMutationSupport:
    @staticmethod
    def _normalize_managed_kb_root_path(path: str | None) -> str | None:
        raw_path = str(path or "").strip()
        if not raw_path:
            return None
        if raw_path == "/":
            return "/"
        parts = [str(part or "").strip() for part in raw_path.split("/") if str(part or "").strip()]
        if not parts:
            return "/"
        return f"/{'/'.join(parts)}"

    @classmethod
    def _managed_kb_root_paths_overlap(cls, left: str | None, right: str | None) -> bool:
        normalized_left = cls._normalize_managed_kb_root_path(left)
        normalized_right = cls._normalize_managed_kb_root_path(right)
        if not normalized_left or not normalized_right:
            return False
        if normalized_left == "/" or normalized_right == "/":
            return True
        return (
            normalized_left == normalized_right
            or normalized_left.startswith(f"{normalized_right}/")
            or normalized_right.startswith(f"{normalized_left}/")
        )

    @staticmethod
    def _requires_manager_assignment(
        *,
        role: str,
        company_id: int | None,
        department_id: int | None,
    ) -> bool:
        return role == "viewer" and (company_id is not None or department_id is not None)

    def _resolve_organization_context(
        self,
        *,
        company_id: int | None,
        department_id: int | None,
    ) -> UserOrganizationContext:
        if company_id is not None and not self._port.get_company(company_id):
            raise self._error("company_not_found")

        department = None
        if department_id is not None:
            department = self._port.get_department(department_id)
            if not department:
                raise self._error("department_not_found")

        self._validate_company_department_relation(company_id=company_id, department=department)
        return UserOrganizationContext(
            company_id=company_id,
            department_id=department_id,
            department=department,
        )

    def _resolve_create_access_assignment(
        self,
        *,
        user_data,
        role: str,
        company_id: int | None,
        department_id: int | None,
    ) -> UserAccessAssignment:
        require_manager = self._requires_manager_assignment(
            role=role,
            company_id=company_id,
            department_id=department_id,
        )
        manager_user_id = self._validate_manager_user_id(
            user_id=None,
            manager_user_id=user_data.manager_user_id,
            company_id=company_id,
            require_sub_admin=require_manager,
        )
        if require_manager and not manager_user_id:
            raise self._error("manager_user_required_for_viewer")

        managed_kb_root_node_id = self._normalize_managed_kb_root_node_id(
            user_data.managed_kb_root_node_id
        )
        if role == "sub_admin":
            managed_kb_root_node_id, managed_kb_root_path = self._validate_managed_kb_root_node(
                company_id=company_id,
                node_id=managed_kb_root_node_id,
                required=True,
            )
            self._validate_managed_kb_root_assignment_conflict(
                company_id=company_id,
                user_id=None,
                node_id=managed_kb_root_node_id,
                node_path=managed_kb_root_path,
            )
            manager_user_id = None
        else:
            managed_kb_root_node_id = None

        return UserAccessAssignment(
            manager_user_id=manager_user_id,
            managed_kb_root_node_id=managed_kb_root_node_id,
        )

    def _resolve_update_access_assignment(
        self,
        *,
        user_id: str,
        current_user,
        user_data,
        fields_set: set[str],
        effective_role: str,
        company_id: int | None,
        department_id: int | None,
    ) -> UserAccessAssignment:
        require_manager = self._requires_manager_assignment(
            role=effective_role,
            company_id=company_id,
            department_id=department_id,
        )
        manager_user_id = None
        if "manager_user_id" in fields_set:
            manager_user_id = self._validate_manager_user_id(
                user_id=user_id,
                manager_user_id=user_data.manager_user_id,
                company_id=company_id,
                require_sub_admin=require_manager,
            )

        if require_manager:
            if "manager_user_id" in fields_set and not manager_user_id:
                raise self._error("manager_user_required_for_viewer")
            if "manager_user_id" not in fields_set:
                if not getattr(current_user, "manager_user_id", None):
                    raise self._error("manager_user_required_for_viewer")
                self._validate_manager_user_id(
                    user_id=user_id,
                    manager_user_id=getattr(current_user, "manager_user_id", None),
                    company_id=company_id,
                    require_sub_admin=True,
                )

        managed_kb_root_node_id = getattr(current_user, "managed_kb_root_node_id", None)
        if effective_role == "sub_admin":
            if "managed_kb_root_node_id" in fields_set:
                managed_kb_root_node_id = user_data.managed_kb_root_node_id
            managed_kb_root_node_id, managed_kb_root_path = self._validate_managed_kb_root_node(
                company_id=company_id,
                node_id=managed_kb_root_node_id,
                required=True,
            )
            self._validate_managed_kb_root_assignment_conflict(
                company_id=company_id,
                user_id=user_id,
                node_id=managed_kb_root_node_id,
                node_path=managed_kb_root_path,
            )
            manager_user_id = None
        else:
            managed_kb_root_node_id = None

        return UserAccessAssignment(
            manager_user_id=manager_user_id,
            managed_kb_root_node_id=managed_kb_root_node_id,
        )

    def _resolve_create_group_ids(self, *, user_data, role: str) -> list[int]:
        group_ids = list(user_data.group_ids or [])
        for group_id in group_ids:
            if not self._port.get_permission_group(group_id):
                raise self._error(f"permission_group_not_found:{group_id}")

        if role == "viewer":
            return []

        if group_ids:
            return group_ids

        group_id = user_data.group_id
        if not group_id:
            default_group = self._port.get_group_by_name("viewer")
            if default_group:
                group_id = default_group["group_id"]
            else:
                raise self._error("default_permission_group_not_found")
        return [group_id] if group_id else []

    def _resolve_update_group_ids(self, *, user_data) -> list[int] | None:
        group_ids = user_data.group_ids
        if group_ids is not None:
            for group_id in group_ids:
                if not self._port.get_permission_group(group_id):
                    raise self._error(f"permission_group_not_found:{group_id}")
            return group_ids

        if user_data.group_id is not None:
            group = self._port.get_permission_group(user_data.group_id)
            if not group:
                raise self._error("permission_group_not_found")
            return [user_data.group_id]

        return None

    def _validate_managed_kb_root_assignment_conflict(
        self,
        *,
        company_id: int | None,
        user_id: str | None,
        node_id: str | None,
        node_path: str | None,
    ) -> None:
        clean_node_id = self._normalize_managed_kb_root_node_id(node_id)
        normalized_target_path = self._normalize_managed_kb_root_path(node_path)
        if company_id is None or not clean_node_id or not normalized_target_path:
            return

        assigned_users = self._port.list_users(
            q=None,
            role="sub_admin",
            status="active",
            group_id=None,
            company_id=company_id,
            department_id=None,
            created_from_ms=None,
            created_to_ms=None,
            manager_user_id=None,
            limit=1000,
        )
        current_user_id = str(user_id or "").strip()
        for assigned_user in assigned_users or []:
            assigned_user_id = str(getattr(assigned_user, "user_id", "") or "").strip()
            if current_user_id and assigned_user_id == current_user_id:
                continue

            assigned_node_id = self._normalize_managed_kb_root_node_id(
                getattr(assigned_user, "managed_kb_root_node_id", None)
            )
            if not assigned_node_id:
                continue

            assigned_path = self._normalize_managed_kb_root_path(
                self._port.get_managed_kb_root_path(
                    company_id=company_id,
                    node_id=assigned_node_id,
                )
            )
            if not assigned_path:
                continue

            if self._managed_kb_root_paths_overlap(normalized_target_path, assigned_path):
                raise self._error("managed_kb_root_node_conflict", status_code=409)

    def _normalize_tool_ids(self, raw_tool_ids: list[str] | None) -> list[str]:
        try:
            return normalize_assignable_tool_ids(raw_tool_ids)
        except ValueError as exc:
            raise self._error(str(exc)) from exc

    def _resolve_create_tool_ids(self, *, user_data, role: str) -> list[str]:
        tool_ids = self._normalize_tool_ids(user_data.tool_ids)
        if role == "sub_admin":
            return tool_ids
        if tool_ids:
            raise self._error("tool_assignment_role_not_supported")
        return []

    def _resolve_update_tool_ids(self, *, user_data, role: str) -> list[str] | None:
        if user_data.tool_ids is None:
            return None
        tool_ids = self._normalize_tool_ids(user_data.tool_ids)
        if role in {"sub_admin", "viewer"}:
            return tool_ids
        if tool_ids:
            raise self._error("tool_assignment_role_not_supported")
        return []

    @staticmethod
    def _is_disable_applied_now(
        *,
        status: str | None,
        disable_login_enabled: bool | None,
        disable_login_until_ms: int | None,
    ) -> bool:
        if status is not None and status != "active":
            return True
        if not disable_login_enabled:
            return False
        if disable_login_until_ms is None:
            return True
        return disable_login_until_ms > int(time.time() * 1000)

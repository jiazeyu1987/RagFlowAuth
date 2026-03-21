from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Optional, Protocol

from backend.core.roles import VALID_ROLES
from backend.models.user import UserCreate, UserResponse, UserUpdate
from backend.services.users.account_status import is_login_disabled_now

VALID_USER_STATUSES = {"active", "inactive"}


class UsersPort(Protocol):
    def list_users(
        self,
        *,
        q: Optional[str],
        role: Optional[str],
        status: Optional[str],
        group_id: Optional[int],
        company_id: Optional[int],
        department_id: Optional[int],
        created_from_ms: Optional[int],
        created_to_ms: Optional[int],
        limit: int,
    ): ...

    def get_user(self, user_id: str): ...
    def create_user(self, **kwargs): ...
    def update_user(self, **kwargs): ...
    def delete_user(self, user_id: str) -> bool: ...
    def update_password(self, user_id: str, new_password: str) -> None: ...
    def set_user_permission_groups(self, user_id: str, group_ids: list[int]) -> None: ...
    def enforce_login_session_limit(self, user_id: str, max_sessions: int) -> list[str]: ...
    def get_permission_group(self, group_id: int): ...
    def get_group_by_name(self, name: str): ...
    def get_company(self, company_id: int): ...
    def get_department(self, department_id: int): ...
    def get_login_session_summary(self, user_id: str, idle_timeout_minutes: int | None): ...
    def get_login_session_summaries(self, idle_timeout_by_user: dict[str, int | None]): ...


@dataclass
class UserManagementError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class UserManagementManager:
    """
    Framework-agnostic user domain manager.
    """

    def __init__(self, port: UsersPort):
        self._port = port

    @staticmethod
    def _normalize_login_policy(
        *,
        max_login_sessions: int | None,
        idle_timeout_minutes: int | None,
        for_create: bool,
    ) -> tuple[int | None, int | None]:
        max_value = max_login_sessions
        idle_value = idle_timeout_minutes

        if for_create and max_value is None:
            max_value = 3
        if for_create and idle_value is None:
            idle_value = 120

        if max_value is not None:
            try:
                max_value = int(max_value)
            except Exception as e:
                raise UserManagementError("invalid_max_login_sessions") from e
            if max_value < 1 or max_value > 1000:
                raise UserManagementError("max_login_sessions_out_of_range")

        if idle_value is not None:
            try:
                idle_value = int(idle_value)
            except Exception as e:
                raise UserManagementError("invalid_idle_timeout_minutes") from e
            if idle_value < 1 or idle_value > 43_200:
                raise UserManagementError("idle_timeout_minutes_out_of_range")

        return max_value, idle_value

    @staticmethod
    def _normalize_user_status(status: str | None, *, for_create: bool) -> str | None:
        if status is None:
            return "active" if for_create else None
        normalized = str(status or "").strip().lower()
        if not normalized:
            return "active" if for_create else None
        if normalized not in VALID_USER_STATUSES:
            raise UserManagementError("invalid_user_status")
        return normalized

    @staticmethod
    def _normalize_disable_policy(
        *,
        disable_login_enabled: bool | None,
        disable_login_until_ms: int | None,
        for_create: bool,
    ) -> tuple[bool | None, int | None]:
        enabled = disable_login_enabled
        until = disable_login_until_ms

        if for_create and enabled is None:
            enabled = False

        if enabled is None and until is None:
            return None, None

        if enabled is None:
            enabled = bool(until)
        enabled = bool(enabled)

        if not enabled:
            return False, None

        if until is None:
            return True, None

        try:
            until_value = int(until)
        except Exception as e:
            raise UserManagementError("invalid_disable_login_until_ms") from e

        if until_value <= int(time.time() * 1000):
            raise UserManagementError("disable_login_until_must_be_future")
        return True, until_value

    def _build_permission_groups(self, group_ids: list[int] | None) -> list[dict]:
        result: list[dict] = []
        for gid in group_ids or []:
            pg = self._port.get_permission_group(gid)
            if pg:
                result.append({"group_id": gid, "group_name": pg.get("group_name", "")})
        return result

    def _to_response(self, user, session_summary: dict[str, int | None] | None = None) -> UserResponse:
        group = self._port.get_permission_group(user.group_id) if user.group_id else None
        company = self._port.get_company(user.company_id) if getattr(user, "company_id", None) else None
        department = self._port.get_department(user.department_id) if getattr(user, "department_id", None) else None

        active_count = 0
        active_last = None
        if session_summary:
            try:
                active_count = int(session_summary.get("active_session_count") or 0)
            except Exception:
                active_count = 0
            active_last = session_summary.get("active_session_last_activity_at_ms")
            if active_last is not None:
                try:
                    active_last = int(active_last)
                except Exception:
                    active_last = None

        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            company_id=getattr(user, "company_id", None),
            company_name=company.name if company else None,
            department_id=getattr(user, "department_id", None),
            department_name=department.name if department else None,
            group_id=user.group_id,
            group_name=group["group_name"] if group else None,
            group_ids=user.group_ids,
            permission_groups=self._build_permission_groups(user.group_ids),
            role=user.role,
            status=user.status,
            can_change_password=bool(getattr(user, "can_change_password", True)),
            disable_login_enabled=bool(getattr(user, "disable_login_enabled", False)),
            disable_login_until_ms=(
                int(getattr(user, "disable_login_until_ms"))
                if getattr(user, "disable_login_until_ms", None) is not None
                else None
            ),
            login_disabled=is_login_disabled_now(user),
            max_login_sessions=int(getattr(user, "max_login_sessions", 3) or 3),
            idle_timeout_minutes=int(getattr(user, "idle_timeout_minutes", 120) or 120),
            active_session_count=active_count,
            active_session_last_activity_at_ms=active_last,
            created_at_ms=user.created_at_ms,
            last_login_at_ms=user.last_login_at_ms,
        )

    def list_users(
        self,
        *,
        q: Optional[str],
        role: Optional[str],
        group_id: Optional[int],
        company_id: Optional[int],
        department_id: Optional[int],
        status: Optional[str],
        created_from_ms: Optional[int],
        created_to_ms: Optional[int],
        limit: int,
    ) -> list[UserResponse]:
        users = self._port.list_users(
            q=q,
            role=role,
            status=status,
            group_id=group_id,
            company_id=company_id,
            department_id=department_id,
            created_from_ms=created_from_ms,
            created_to_ms=created_to_ms,
            limit=limit,
        )
        idle_by_user = {
            u.user_id: int(getattr(u, "idle_timeout_minutes", 120) or 120)
            for u in users
            if getattr(u, "user_id", None)
        }
        summaries = self._port.get_login_session_summaries(idle_by_user)
        return [self._to_response(u, summaries.get(u.user_id)) for u in users]

    def create_user(self, *, user_data: UserCreate, created_by: str) -> UserResponse:
        role = user_data.role or "viewer"
        if role not in VALID_ROLES:
            raise UserManagementError(f"Invalid role: {role}")
        status = self._normalize_user_status(user_data.status, for_create=True)

        if user_data.company_id is not None and not self._port.get_company(user_data.company_id):
            raise UserManagementError("company_not_found")
        if user_data.department_id is not None and not self._port.get_department(user_data.department_id):
            raise UserManagementError("department_not_found")

        max_login_sessions, idle_timeout_minutes = self._normalize_login_policy(
            max_login_sessions=user_data.max_login_sessions,
            idle_timeout_minutes=user_data.idle_timeout_minutes,
            for_create=True,
        )
        disable_login_enabled, disable_login_until_ms = self._normalize_disable_policy(
            disable_login_enabled=user_data.disable_login_enabled,
            disable_login_until_ms=user_data.disable_login_until_ms,
            for_create=True,
        )

        group_ids = user_data.group_ids
        if not group_ids:
            group_id = user_data.group_id
            if not group_id:
                default_group = self._port.get_group_by_name("viewer")
                if default_group:
                    group_id = default_group["group_id"]
                else:
                    raise UserManagementError("default_permission_group_not_found")
            group_ids = [group_id] if group_id else []

        for gid in group_ids:
            if not self._port.get_permission_group(gid):
                raise UserManagementError(f"permission_group_not_found:{gid}")

        user = self._port.create_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
            company_id=user_data.company_id,
            department_id=user_data.department_id,
            role=role,
            group_id=None,
            status=status,
            max_login_sessions=max_login_sessions,
            idle_timeout_minutes=idle_timeout_minutes,
            can_change_password=bool(user_data.can_change_password),
            disable_login_enabled=bool(disable_login_enabled),
            disable_login_until_ms=disable_login_until_ms,
            created_by=created_by,
        )

        if group_ids:
            self._port.set_user_permission_groups(user.user_id, group_ids)

        user = self._port.get_user(user.user_id)
        return self._to_response(user)

    def get_user(self, user_id: str) -> UserResponse:
        user = self._port.get_user(user_id)
        if not user:
            raise UserManagementError("user_not_found", status_code=404)
        summary = self._port.get_login_session_summary(
            user.user_id,
            int(getattr(user, "idle_timeout_minutes", 120) or 120),
        )
        return self._to_response(user, summary)

    def update_user(self, *, user_id: str, user_data: UserUpdate) -> UserResponse:
        current_user = self._port.get_user(user_id)
        if not current_user:
            raise UserManagementError("user_not_found", status_code=404)

        role = user_data.role
        if role is not None and role not in VALID_ROLES:
            raise UserManagementError(f"Invalid role: {role}")
        status = self._normalize_user_status(user_data.status, for_create=False)

        if user_data.company_id is not None and not self._port.get_company(user_data.company_id):
            raise UserManagementError("company_not_found")
        if user_data.department_id is not None and not self._port.get_department(user_data.department_id):
            raise UserManagementError("department_not_found")

        max_login_sessions, idle_timeout_minutes = self._normalize_login_policy(
            max_login_sessions=user_data.max_login_sessions,
            idle_timeout_minutes=user_data.idle_timeout_minutes,
            for_create=False,
        )
        disable_login_enabled, disable_login_until_ms = self._normalize_disable_policy(
            disable_login_enabled=user_data.disable_login_enabled,
            disable_login_until_ms=user_data.disable_login_until_ms,
            for_create=False,
        )
        can_change_password = (
            bool(user_data.can_change_password) if user_data.can_change_password is not None else None
        )

        disable_now = False
        if status is not None and status != "active":
            disable_now = True
        if disable_login_enabled:
            if disable_login_until_ms is None:
                disable_now = True
            else:
                disable_now = disable_login_until_ms > int(time.time() * 1000)

        is_builtin_admin = str(getattr(current_user, "username", "") or "").strip().lower() == "admin"
        if is_builtin_admin and disable_now:
            raise UserManagementError("admin_user_cannot_be_disabled")

        group_ids = user_data.group_ids
        if group_ids is not None:
            for gid in group_ids:
                if not self._port.get_permission_group(gid):
                    raise UserManagementError(f"permission_group_not_found:{gid}")
        elif user_data.group_id is not None:
            group = self._port.get_permission_group(user_data.group_id)
            if not group:
                raise UserManagementError("permission_group_not_found")
            group_ids = [user_data.group_id]

        user = self._port.update_user(
            user_id=user_id,
            email=user_data.email,
            company_id=user_data.company_id,
            department_id=user_data.department_id,
            role=role,
            group_id=None,
            status=status,
            max_login_sessions=max_login_sessions,
            idle_timeout_minutes=idle_timeout_minutes,
            can_change_password=can_change_password,
            disable_login_enabled=disable_login_enabled,
            disable_login_until_ms=disable_login_until_ms,
        )
        if not user:
            raise UserManagementError("user_not_found", status_code=404)

        if group_ids is not None:
            self._port.set_user_permission_groups(user.user_id, group_ids)

        if max_login_sessions is not None:
            self._port.enforce_login_session_limit(user.user_id, max_login_sessions)

        user = self._port.get_user(user.user_id)
        summary = self._port.get_login_session_summary(
            user.user_id,
            int(getattr(user, "idle_timeout_minutes", 120) or 120),
        )
        return self._to_response(user, summary)

    def delete_user(self, user_id: str) -> None:
        if not self._port.delete_user(user_id):
            raise UserManagementError("user_not_found", status_code=404)

    def reset_password(self, user_id: str, new_password: str) -> None:
        user = self._port.get_user(user_id)
        if not user:
            raise UserManagementError("user_not_found", status_code=404)
        self._port.update_password(user_id, new_password)

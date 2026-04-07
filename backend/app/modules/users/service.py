from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from backend.models.user import UserCreate, UserUpdate, UserResponse

from backend.app.modules.users.repo import UsersRepo
from backend.services.users.manager import UserManagementError, UserManagementManager


class UsersService:
    def __init__(self, repo: UsersRepo):
        self._manager = UserManagementManager(repo)

    @staticmethod
    def _raise(err: UserManagementError) -> None:
        raise HTTPException(status_code=err.status_code, detail=err.code) from err

    def _call_manager(self, method_name: str, /, **kwargs):
        method = getattr(self._manager, method_name)
        try:
            return method(**kwargs)
        except UserManagementError as err:
            self._raise(err)

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
        manager_user_id: Optional[str] = None,
        limit: int,
    ) -> list[UserResponse]:
        return self._call_manager(
            "list_users",
            q=q,
            role=role,
            group_id=group_id,
            company_id=company_id,
            department_id=department_id,
            status=status,
            created_from_ms=created_from_ms,
            created_to_ms=created_to_ms,
            manager_user_id=manager_user_id,
            limit=limit,
        )

    def create_user(self, *, user_data: UserCreate, created_by: str) -> UserResponse:
        return self._call_manager("create_user", user_data=user_data, created_by=created_by)

    def get_user(self, *, user_id: str) -> UserResponse:
        return self._call_manager("get_user", user_id=user_id)

    def update_user(self, *, user_id: str, user_data: UserUpdate) -> UserResponse:
        return self._call_manager("update_user", user_id=user_id, user_data=user_data)

    def delete_user(self, *, user_id: str) -> None:
        self._call_manager("delete_user", user_id=user_id)

    def reset_password(self, *, user_id: str, new_password: str) -> None:
        self._call_manager("reset_password", user_id=user_id, new_password=new_password)

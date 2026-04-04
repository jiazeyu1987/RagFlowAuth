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
        try:
            return self._manager.list_users(
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
        except UserManagementError as e:
            self._raise(e)

    def create_user(self, *, user_data: UserCreate, created_by: str) -> UserResponse:
        try:
            return self._manager.create_user(user_data=user_data, created_by=created_by)
        except UserManagementError as e:
            self._raise(e)

    def get_user(self, user_id: str) -> UserResponse:
        try:
            return self._manager.get_user(user_id)
        except UserManagementError as e:
            self._raise(e)

    def update_user(self, *, user_id: str, user_data: UserUpdate) -> UserResponse:
        try:
            return self._manager.update_user(user_id=user_id, user_data=user_data)
        except UserManagementError as e:
            self._raise(e)

    def delete_user(self, user_id: str) -> None:
        try:
            self._manager.delete_user(user_id)
        except UserManagementError as e:
            self._raise(e)

    def reset_password(self, user_id: str, new_password: str) -> None:
        try:
            self._manager.reset_password(user_id, new_password)
        except UserManagementError as e:
            self._raise(e)

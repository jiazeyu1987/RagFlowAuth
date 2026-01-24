from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Optional

from backend.app.core.auth import get_deps
from backend.app.core.authz import AdminOnly
from backend.app.dependencies import AppDependencies
from backend.models.user import UserCreate, UserUpdate, UserResponse

from backend.app.modules.users.repo import UsersRepo
from backend.app.modules.users.service import UsersService


router = APIRouter()


def get_service(deps: AppDependencies = Depends(get_deps)) -> UsersService:
    return UsersService(UsersRepo(deps))


@router.get("", response_model=list[UserResponse])
async def list_users(
    _: AdminOnly,
    service: UsersService = Depends(get_service),
    q: Optional[str] = None,
    role: Optional[str] = None,
    group_id: Optional[int] = None,
    company_id: Optional[int] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    created_from_ms: Optional[int] = None,
    created_to_ms: Optional[int] = None,
    limit: int = 100,
):
    return service.list_users(
        q=q,
        role=role,
        group_id=group_id,
        company_id=company_id,
        department_id=department_id,
        status=status,
        created_from_ms=created_from_ms,
        created_to_ms=created_to_ms,
        limit=limit,
    )


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    payload: AdminOnly,
    service: UsersService = Depends(get_service),
):
    return service.create_user(user_data=user_data, created_by=payload.sub)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    _: AdminOnly,
    service: UsersService = Depends(get_service),
):
    return service.get_user(user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    _: AdminOnly,
    service: UsersService = Depends(get_service),
):
    return service.update_user(user_id=user_id, user_data=user_data)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    _: AdminOnly,
    service: UsersService = Depends(get_service),
):
    service.delete_user(user_id)
    return {"message": "用户已删除"}


@router.put("/{user_id}/password")
async def reset_password(
    user_id: str,
    new_password: str,
    _: AdminOnly,
    service: UsersService = Depends(get_service),
):
    service.reset_password(user_id, new_password)
    return {"message": "密码已重置"}

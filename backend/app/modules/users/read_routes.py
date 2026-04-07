from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from backend.app.core.authz import AuthContextDep
from backend.app.modules.users.dependencies import UserStoreDep, UsersServiceDep
from backend.app.modules.users import reads as user_reads
from backend.models.user import UserResponse


def register_read_routes(router: APIRouter) -> None:
    @router.get("", response_model=list[UserResponse])
    async def list_users(
        ctx: AuthContextDep,
        service: UsersServiceDep,
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
        return user_reads.list_users_result(
            ctx=ctx,
            service=service,
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

    @router.get("/{user_id}", response_model=UserResponse)
    async def get_user(
        user_id: str,
        ctx: AuthContextDep,
        user_store: UserStoreDep,
        service: UsersServiceDep,
    ):
        return user_reads.get_user_result(
            ctx=ctx,
            user_store=user_store,
            service=service,
            user_id=user_id,
        )

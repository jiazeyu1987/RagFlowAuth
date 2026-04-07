from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.modules.users.dependencies import UserStoreDep, UsersServiceDep
from backend.app.modules.users import writes as user_writes
from backend.app.modules.users.schemas import ResultEnvelope, UserEnvelope
from backend.models.user import UserCreate, UserUpdate


def register_write_routes(router: APIRouter) -> None:
    @router.post("", response_model=UserEnvelope, status_code=201)
    async def create_user(
        user_data: UserCreate,
        payload: AdminOnly,
        service: UsersServiceDep,
    ):
        return user_writes.create_user_result(
            service=service,
            user_data=user_data,
            created_by=payload.sub,
        )

    @router.put("/{user_id}", response_model=UserEnvelope)
    async def update_user(
        user_id: str,
        user_data: UserUpdate,
        ctx: AuthContextDep,
        user_store: UserStoreDep,
        service: UsersServiceDep,
    ):
        return user_writes.update_user_result(
            ctx=ctx,
            user_store=user_store,
            service=service,
            user_id=user_id,
            user_data=user_data,
        )

    @router.delete("/{user_id}", response_model=ResultEnvelope)
    async def delete_user(
        user_id: str,
        _: AdminOnly,
        service: UsersServiceDep,
    ):
        return user_writes.delete_user_result(service=service, user_id=user_id)

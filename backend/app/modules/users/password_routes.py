from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.core.authz import AuthContextDep
from backend.app.modules.users.dependencies import GlobalAppDepsDep, UsersServiceDep
from backend.app.modules.users import passwords as user_passwords
from backend.app.modules.users.schemas import ResetPasswordRequest, ResultEnvelope


def register_password_routes(router: APIRouter) -> None:
    @router.put("/{user_id}/password", response_model=ResultEnvelope)
    async def reset_password(
        user_id: str,
        body: ResetPasswordRequest,
        ctx: AuthContextDep,
        request: Request,
        deps: GlobalAppDepsDep,
        service: UsersServiceDep,
    ):
        return user_passwords.reset_password_result(
            ctx=ctx,
            deps=deps,
            request=request,
            service=service,
            user_id=user_id,
            new_password=body.new_password,
        )

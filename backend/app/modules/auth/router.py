from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.app.core.auth import get_deps
from backend.app.core.authz import AuthContextDep
from backend.app.dependencies import AppDependencies
from backend.models.auth import ChangePasswordRequest, LoginRequest, TokenResponse
from backend.services.auth_flow_service import login as auth_login
from backend.services.auth_flow_service import logout as auth_logout
from backend.services.auth_flow_service import refresh as auth_refresh
from backend.services.auth_me_service import build_auth_me_payload
from backend.services.user_store import hash_password
from backend.services.users import validate_password_requirements

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    response: Response,
    deps: AppDependencies = Depends(get_deps),
):
    return auth_login(
        credentials=credentials,
        response=response,
        deps=deps,
    )


@router.post("/refresh")
async def refresh_token(
    request: Request,
    deps: AppDependencies = Depends(get_deps),
):
    return await auth_refresh(request=request, deps=deps)


@router.post("/logout")
async def logout(request: Request, response: Response, deps: AppDependencies = Depends(get_deps)):
    return await auth_logout(request=request, response=response, deps=deps)


@router.get("/me")
def get_current_user(
    ctx: AuthContextDep,
):
    return build_auth_me_payload(deps=ctx.deps, user=ctx.user, snapshot=ctx.snapshot)


@router.put("/password")
def change_password(
    request_data: ChangePasswordRequest,
    ctx: AuthContextDep,
):
    """
    Change password for authenticated user.

    Requires:
    - Correct old password
    - New password meets validation requirements
    """
    deps = ctx.deps
    user = ctx.user

    if not bool(getattr(user, "can_change_password", True)):
        raise HTTPException(status_code=403, detail="password_change_disabled")

    # Verify old password
    if hash_password(request_data.old_password) != user.password_hash:
        raise HTTPException(status_code=400, detail="旧密码错误")

    # Validate new password requirements
    if not validate_password_requirements(
        password=request_data.new_password,
        old_password=request_data.old_password,
    ):
        # Check specific validation error for better error messages
        if len(request_data.new_password) < 6:
            raise HTTPException(status_code=400, detail="密码不符合要求：密码长度至少6个字符")
        if request_data.new_password == request_data.old_password:
            raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")
        raise HTTPException(status_code=400, detail="密码不符合要求：必须包含字母和数字，且不能使用常见密码")

    # Update password
    deps.user_store.update_password(user.user_id, request_data.new_password)

    logger.info(f"Password changed for user {user.username}")

    return {"message": "密码修改成功"}

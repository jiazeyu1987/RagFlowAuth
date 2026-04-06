from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.app.core.auth import get_deps, get_global_deps
from backend.app.core.authz import AuthContextDep
from backend.app.dependencies import AppDependencies
from backend.models.auth import ChangePasswordRequest, LoginRequest, ResultEnvelope, TokenResponse
from backend.services.auth_flow_service import login as auth_login
from backend.services.auth_flow_service import logout as auth_logout
from backend.services.auth_flow_service import refresh as auth_refresh
from backend.services.auth_me_service import build_auth_me_payload
from backend.services.users import validate_password_requirements, verify_password

router = APIRouter()
logger = logging.getLogger(__name__)


def _result_envelope(message: str) -> dict[str, dict[str, str]]:
    return {"result": {"message": message}}


def _password_validation_error(request_data: ChangePasswordRequest) -> str | None:
    if validate_password_requirements(
        password=request_data.new_password,
        old_password=request_data.old_password,
    ):
        return None
    if len(request_data.new_password) < 6:
        return "new_password_too_short"
    if request_data.new_password == request_data.old_password:
        return "new_password_same_as_old"
    return "new_password_requirements_not_met"


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


@router.post("/logout", response_model=ResultEnvelope)
async def logout(request: Request, response: Response, deps: AppDependencies = Depends(get_deps)):
    return await auth_logout(request=request, response=response, deps=deps)


@router.get("/me")
def get_current_user(
    ctx: AuthContextDep,
):
    return build_auth_me_payload(deps=ctx.deps, user=ctx.user, snapshot=ctx.snapshot)


@router.put("/password", response_model=ResultEnvelope)
def change_password(
    request_data: ChangePasswordRequest,
    request: Request,
    ctx: AuthContextDep,
):
    deps = get_global_deps(request)
    user = deps.user_store.get_by_user_id(ctx.user.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")

    if not bool(getattr(user, "can_change_password", True)):
        raise HTTPException(status_code=403, detail="password_change_disabled")

    old_password_ok, _ = verify_password(request_data.old_password, user.password_hash)
    if not old_password_ok:
        raise HTTPException(status_code=400, detail="old_password_incorrect")

    validation_error = _password_validation_error(request_data)
    if validation_error is not None:
        raise HTTPException(status_code=400, detail=validation_error)

    if deps.user_store.password_matches_recent_history(user.user_id, request_data.new_password, limit=5):
        raise HTTPException(status_code=400, detail="new_password_reused_from_recent_history")

    deps.user_store.update_password(user.user_id, request_data.new_password)

    logger.info("Password changed for user %s", user.username)

    return _result_envelope("password_changed")

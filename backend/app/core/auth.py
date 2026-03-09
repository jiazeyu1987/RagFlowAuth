from __future__ import annotations

from typing import Annotated

from authx import TokenPayload
from fastapi import Depends, HTTPException, Request

from backend.core.security import auth
from backend.app.dependencies import AppDependencies
from backend.services.auth_flow_service import payload_sid, resolve_request_token
from backend.services.auth_session import AuthSessionError


def get_deps(request: Request) -> AppDependencies:
    return request.app.state.deps


async def get_current_payload(request: Request) -> TokenPayload:
    """
    Resolve the current access-token payload.

    Accepts:
    - Authorization: Bearer <access_token> (frontend default)
    - access_token cookie (AuthX compatible)
    - token query param (AuthX compatible)

    Always returns 401 (not 422) when token is missing/invalid.
    """
    request_token = await resolve_request_token(request, token_type="access")

    if not request_token:
        raise HTTPException(status_code=401, detail="Missing access token")

    try:
        payload = auth.verify_token(request_token, verify_type=True)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid access token")

    deps = getattr(getattr(request, "app", None), "state", None)
    deps = getattr(deps, "deps", None)
    if deps is None:
        return payload

    user_store = getattr(deps, "user_store", None)
    session_store = getattr(deps, "auth_session_store", None)
    session_manager = getattr(deps, "auth_session_manager", None)
    if not user_store or (not session_store and not session_manager):
        return payload

    user = user_store.get_by_user_id(payload.sub)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if str(getattr(user, "status", "") or "").lower() != "active":
        raise HTTPException(status_code=403, detail="account_inactive")

    sid = payload_sid(payload)
    if not sid:
        raise HTTPException(status_code=401, detail="missing_session_id")

    if session_manager is not None:
        try:
            session_manager.validate_access_session(
                session_id=sid,
                user_id=user.user_id,
                idle_timeout_minutes=getattr(user, "idle_timeout_minutes", 120),
            )
        except AuthSessionError as e:
            raise HTTPException(status_code=e.status_code, detail=f"session_invalid:{e.code}") from e
    else:
        ok, reason = session_store.validate_session(
            session_id=sid,
            user_id=user.user_id,
            idle_timeout_minutes=getattr(user, "idle_timeout_minutes", 120),
            touch=True,
            mark_refresh=False,
        )
        if not ok:
            raise HTTPException(status_code=401, detail=f"session_invalid:{reason}")

    return payload


AuthRequired = Annotated[TokenPayload, Depends(get_current_payload)]

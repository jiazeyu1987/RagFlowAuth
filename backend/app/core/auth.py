from __future__ import annotations

from typing import Annotated

from authx import TokenPayload
from fastapi import Depends, HTTPException, Request

from backend.app.core.tenant import company_id_from_payload, company_id_from_user
from backend.app.dependencies import AppDependencies, get_global_dependencies, get_tenant_dependencies
from backend.core.security import auth
from backend.services.auth_flow_service import payload_sid, resolve_request_token
from backend.services.auth_session import AuthSessionError
from backend.services.users import resolve_login_block


def get_global_deps(request: Request) -> AppDependencies:
    return get_global_dependencies(request.app)


def _is_auth_endpoint(request: Request) -> bool:
    path = str(getattr(getattr(request, "url", None), "path", "") or "")
    return path.startswith("/api/auth/")


def _company_id_for_request(
    request: Request,
    *,
    payload: TokenPayload | None = None,
    user: object | None = None,
) -> int | None:
    try:
        cid = company_id_from_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid_company_id_claim") from exc
    if cid is not None:
        return cid

    try:
        uid = company_id_from_user(user)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="invalid_user_company_id") from exc
    if uid is not None:
        return uid

    if payload is None:
        return None

    global_deps = get_global_deps(request)
    user_store = getattr(global_deps, "user_store", None)
    if not user_store:
        return None
    maybe_user = user_store.get_by_user_id(payload.sub)
    try:
        return company_id_from_user(maybe_user)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="invalid_user_company_id") from exc


def resolve_scoped_deps(
    request: Request,
    *,
    payload: TokenPayload | None = None,
    user: object | None = None,
    force_tenant_scope: bool = False,
) -> AppDependencies:
    cached = getattr(getattr(request, "state", None), "tenant_deps", None)
    if cached is not None:
        return cached

    global_deps = get_global_deps(request)
    if not isinstance(global_deps, AppDependencies):
        return global_deps
    if not force_tenant_scope and _is_auth_endpoint(request):
        return global_deps

    company_id = _company_id_for_request(request, payload=payload, user=user)
    if company_id is None:
        return global_deps

    tenant_deps = get_tenant_dependencies(request.app, company_id=company_id)
    request.state.tenant_company_id = company_id
    request.state.tenant_deps = tenant_deps
    return tenant_deps


async def get_deps(request: Request) -> AppDependencies:
    cached = getattr(getattr(request, "state", None), "tenant_deps", None)
    if cached is not None:
        return cached

    if _is_auth_endpoint(request):
        return get_global_deps(request)

    payload: TokenPayload | None = None
    request_token = await resolve_request_token(request, token_type="access")
    if request_token:
        try:
            payload = auth.verify_token(request_token, verify_type=True)
        except Exception:
            payload = None

    return resolve_scoped_deps(request, payload=payload, force_tenant_scope=False)


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

    deps = get_global_deps(request)

    user_store = getattr(deps, "user_store", None)
    session_store = getattr(deps, "auth_session_store", None)
    session_manager = getattr(deps, "auth_session_manager", None)
    if not user_store or (not session_store and not session_manager):
        return payload

    user = user_store.get_by_user_id(payload.sub)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    blocked, code = resolve_login_block(user)
    if blocked:
        raise HTTPException(status_code=403, detail=code or "account_disabled")

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

    request.state.auth_payload = payload
    request.state.authenticated_user = user
    resolve_scoped_deps(request, payload=payload, user=user, force_tenant_scope=True)

    return payload


AuthRequired = Annotated[TokenPayload, Depends(get_current_payload)]

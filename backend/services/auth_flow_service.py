from __future__ import annotations

import uuid
from datetime import datetime

from authx.schema import RequestToken
from fastapi import HTTPException, Request, Response

from backend.app.dependencies import AppDependencies
from backend.core.security import auth
from backend.models.auth import LoginRequest, TokenResponse
from backend.services.audit_helpers import actor_fields_from_user
from backend.services.auth_session import AuthSessionError
from backend.services.users import resolve_login_block, verify_password


def _header_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    return token or None


async def resolve_request_token(request: Request, *, token_type: str) -> RequestToken | None:
    try:
        if token_type == "access":
            maybe_token = await auth.get_access_token_from_request(request)
        else:
            maybe_token = await auth.get_refresh_token_from_request(request)
        if maybe_token:
            return maybe_token
    except Exception:
        pass

    fallback = _header_bearer_token(request)
    if not fallback:
        return None
    try:
        return RequestToken(token=fallback, type=token_type, location="headers")
    except Exception:
        return None


def _payload_value(payload: object, key: str):
    if hasattr(payload, key):
        return getattr(payload, key)
    try:
        return payload.model_dump().get(key)  # type: ignore[attr-defined]
    except Exception:
        return None


def payload_sid(payload: object) -> str:
    sid = _payload_value(payload, "sid")
    return str(sid or "").strip()


def payload_jti(payload: object) -> str:
    jti = _payload_value(payload, "jti")
    return str(jti or "").strip()


def payload_exp(payload: object):
    exp = _payload_value(payload, "exp")
    if isinstance(exp, datetime):
        return exp
    return exp


def _token_data_for_user(*, user: object, sid: str | None = None) -> dict[str, object] | None:
    data: dict[str, object] = {}
    if sid:
        data["sid"] = sid
    company_id = getattr(user, "company_id", None)
    if company_id is not None and str(company_id).strip() != "":
        data["cid"] = int(company_id)
    return data or None


def login(
    *,
    credentials: LoginRequest,
    response: Response,
    deps: AppDependencies,
) -> TokenResponse:
    user = deps.user_store.get_by_username(credentials.username)
    if not user:
        raise HTTPException(status_code=401, detail="invalid_username_or_password")

    blocked, code = resolve_login_block(user)
    if blocked:
        status_code = 423 if code == "credentials_locked" else 403
        raise HTTPException(status_code=status_code, detail=code or "account_disabled")

    password_ok, needs_rehash = verify_password(credentials.password, user.password_hash)
    if not password_ok:
        locked_until_ms = deps.user_store.record_credential_failure(user.user_id)
        if locked_until_ms is not None:
            raise HTTPException(status_code=423, detail="credentials_locked")
        raise HTTPException(status_code=401, detail="invalid_username_or_password")

    deps.user_store.clear_credential_failures(user.user_id)
    if needs_rehash:
        deps.user_store.update_password(user.user_id, credentials.password)
        refreshed_user = deps.user_store.get_by_user_id(user.user_id)
        if refreshed_user is not None:
            user = refreshed_user

    scopes: list[str] = []
    auth_session_store = getattr(deps, "auth_session_store", None)
    auth_session_manager = getattr(deps, "auth_session_manager", None)

    if auth_session_manager is not None:
        max_sessions = int(getattr(user, "max_login_sessions", 3) or 3)
        try:
            sid = auth_session_manager.issue_session_id_for_login(
                user_id=user.user_id,
                max_sessions=max_sessions,
                reserve_slots=1,
            )
        except AuthSessionError as e:
            raise HTTPException(status_code=e.status_code, detail=e.code) from e
        token_data = _token_data_for_user(user=user, sid=sid)
        refresh_token = auth.create_refresh_token(uid=user.user_id, data=token_data)
        refresh_request_token = RequestToken(token=refresh_token, type="refresh", location="headers")
        refresh_payload = auth.verify_token(refresh_request_token, verify_type=True)

        access_token = auth.create_access_token(uid=user.user_id, scopes=scopes, data=token_data)
        auth_session_manager.bind_refresh_session(
            session_id=sid,
            user_id=user.user_id,
            refresh_jti=payload_jti(refresh_payload) or None,
            expires_at=payload_exp(refresh_payload),
        )
    elif auth_session_store is not None:
        max_sessions = int(getattr(user, "max_login_sessions", 3) or 3)
        auth_session_store.enforce_user_session_limit(
            user_id=user.user_id,
            max_sessions=max_sessions,
            reserve_slots=1,
            reason="session_limit_exceeded",
        )
        sid = str(uuid.uuid4())
        token_data = _token_data_for_user(user=user, sid=sid)
        refresh_token = auth.create_refresh_token(uid=user.user_id, data=token_data)
        refresh_request_token = RequestToken(token=refresh_token, type="refresh", location="headers")
        refresh_payload = auth.verify_token(refresh_request_token, verify_type=True)
        access_token = auth.create_access_token(uid=user.user_id, scopes=scopes, data=token_data)
        auth_session_store.create_session(
            session_id=sid,
            user_id=user.user_id,
            refresh_jti=payload_jti(refresh_payload) or None,
            expires_at=payload_exp(refresh_payload),
        )
    else:
        token_data = _token_data_for_user(user=user, sid=None)
        access_token = auth.create_access_token(uid=user.user_id, scopes=scopes, data=token_data)
        refresh_token = auth.create_refresh_token(uid=user.user_id, data=token_data)

    auth.set_access_cookies(access_token, response)
    auth.set_refresh_cookies(refresh_token, response)

    deps.user_store.update_last_login(user.user_id)
    audit = getattr(deps, "audit_log_store", None)
    if audit:
        try:
            audit.log_event(
                action="auth_login",
                actor=user.user_id,
                source="auth",
                meta={"username": user.username},
                **actor_fields_from_user(deps, user),
            )
        except Exception:
            pass

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        scopes=scopes,
    )


async def refresh(*, request: Request, deps: AppDependencies) -> dict[str, str]:
    request_token = await resolve_request_token(request, token_type="refresh")
    if not request_token:
        raise HTTPException(status_code=401, detail="missing_refresh_token")

    try:
        payload = auth.verify_token(request_token, verify_type=True)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"invalid_refresh_token:{e}") from e

    user = deps.user_store.get_by_user_id(payload.sub)
    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")

    blocked, code = resolve_login_block(user)
    if blocked:
        raise HTTPException(status_code=403, detail=code or "account_disabled")

    sid = payload_sid(payload)
    auth_session_store = getattr(deps, "auth_session_store", None)
    auth_session_manager = getattr(deps, "auth_session_manager", None)
    if auth_session_manager is not None:
        if not sid:
            raise HTTPException(status_code=401, detail="missing_session_id")
        try:
            auth_session_manager.validate_refresh_session(
                session_id=sid,
                user_id=user.user_id,
                idle_timeout_minutes=getattr(user, "idle_timeout_minutes", 120),
                refresh_jti=payload_jti(payload) or None,
            )
        except AuthSessionError as e:
            raise HTTPException(status_code=e.status_code, detail=f"session_invalid:{e.code}") from e
    elif auth_session_store is not None:
        if not sid:
            raise HTTPException(status_code=401, detail="missing_session_id")
        ok, reason = auth_session_store.validate_session(
            session_id=sid,
            user_id=user.user_id,
            idle_timeout_minutes=getattr(user, "idle_timeout_minutes", 120),
            refresh_jti=payload_jti(payload) or None,
            mark_refresh=True,
            touch=True,
        )
        if not ok:
            raise HTTPException(status_code=401, detail=f"session_invalid:{reason}")

    scopes: list[str] = []
    token_data = _token_data_for_user(user=user, sid=(sid or None))
    access_token = auth.create_access_token(
        uid=payload.sub,
        scopes=scopes,
        data=token_data,
    )
    return {"access_token": access_token, "token_type": "bearer"}


async def logout(*, request: Request, response: Response, deps: AppDependencies) -> dict[str, str]:
    actor = None
    sid = ""

    token = await resolve_request_token(request, token_type="access")
    if token:
        try:
            payload = auth.verify_token(token, verify_type=True)
            actor = payload.sub
            sid = payload_sid(payload)
        except Exception:
            actor = None
            sid = ""

    auth_session_store = getattr(deps, "auth_session_store", None)
    auth_session_manager = getattr(deps, "auth_session_manager", None)
    if auth_session_manager is not None and sid:
        try:
            auth_session_manager.revoke_session(session_id=sid, reason="logout")
        except Exception:
            pass
    elif auth_session_store is not None and sid:
        try:
            auth_session_store.revoke_session(session_id=sid, reason="logout")
        except Exception:
            pass

    audit = getattr(deps, "audit_log_store", None)
    if audit and actor:
        try:
            user = deps.user_store.get_by_user_id(actor)
            audit.log_event(
                action="auth_logout",
                actor=actor,
                source="auth",
                **(actor_fields_from_user(deps, user) if user else {}),
            )
        except Exception:
            pass
    auth.unset_cookies(response)
    return {"message": "logout_ok"}

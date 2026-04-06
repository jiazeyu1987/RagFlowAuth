from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Annotated, Any

from authx import TokenPayload
from fastapi import Depends, HTTPException, Request

from backend.app.core.auth import get_current_payload, resolve_scoped_deps
from backend.app.core.permission_resolver import PermissionSnapshot, resolve_permissions
from backend.app.dependencies import AppDependencies


@dataclass(frozen=True)
class AuthContext:
    deps: AppDependencies
    payload: TokenPayload
    user: Any
    snapshot: PermissionSnapshot


def get_auth_context(
    request: Request,
    payload: TokenPayload = Depends(get_current_payload),
) -> AuthContext:
    request_state = getattr(request, "state", None)
    authenticated_user = getattr(request_state, "authenticated_user", None)
    deps = resolve_scoped_deps(
        request,
        payload=payload,
        user=authenticated_user,
        force_tenant_scope=True,
    )
    if authenticated_user is not None and getattr(authenticated_user, "user_id", None) == payload.sub:
        user = authenticated_user
    else:
        try:
            user = deps.user_store.get_by_user_id(payload.sub)
        except sqlite3.OperationalError as exc:
            raise HTTPException(status_code=503, detail=f"db_unavailable: {exc}") from exc
    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")
    snapshot = resolve_permissions(deps, user)
    return AuthContext(deps=deps, payload=payload, user=user, snapshot=snapshot)


AuthContextDep = Annotated[AuthContext, Depends(get_auth_context)]


def admin_only(
    ctx: AuthContextDep,
) -> TokenPayload:
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")
    return ctx.payload


AdminOnly = Annotated[TokenPayload, Depends(admin_only)]

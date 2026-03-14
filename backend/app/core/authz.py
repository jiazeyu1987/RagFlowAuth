from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from authx import TokenPayload
from fastapi import Depends, HTTPException
import sqlite3

from backend.app.core.auth import get_current_payload, get_deps
from backend.app.core.permission_resolver import PermissionSnapshot
from backend.app.dependencies import AppDependencies
from backend.services.permission_decision_service import PermissionDecisionError, PermissionDecisionService
from backend.services.super_admin import is_super_admin_user


permission_decider = PermissionDecisionService()


@dataclass(frozen=True)
class AuthContext:
    deps: AppDependencies
    payload: TokenPayload
    user: Any
    snapshot: PermissionSnapshot


def get_auth_context(
    payload: TokenPayload = Depends(get_current_payload),
    deps: AppDependencies = Depends(get_deps),
) -> AuthContext:
    try:
        user = deps.user_store.get_by_user_id(payload.sub)
    except sqlite3.OperationalError as e:
        # Avoid leaking transient sqlite errors as 500s (e.g. during backup/restore IO).
        raise HTTPException(status_code=503, detail=f"db_unavailable: {e}") from e
    if not user:
        # Treat missing user for an authenticated token as unauthorized.
        raise HTTPException(status_code=401, detail="用户不存在")
    snapshot = permission_decider.resolve_snapshot(deps, user)
    return AuthContext(deps=deps, payload=payload, user=user, snapshot=snapshot)


AuthContextDep = Annotated[AuthContext, Depends(get_auth_context)]


def admin_only(
    ctx: AuthContextDep,
) -> TokenPayload:
    try:
        permission_decider.ensure_admin(ctx.snapshot)
    except PermissionDecisionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.reason) from exc
    return ctx.payload


AdminOnly = Annotated[TokenPayload, Depends(admin_only)]


def super_admin_only(
    ctx: AuthContextDep,
) -> TokenPayload:
    try:
        permission_decider.ensure_admin(ctx.snapshot)
    except PermissionDecisionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.reason) from exc
    if not is_super_admin_user(ctx.user):
        raise HTTPException(status_code=403, detail="super_admin_required")
    return ctx.payload


SuperAdminOnly = Annotated[TokenPayload, Depends(super_admin_only)]

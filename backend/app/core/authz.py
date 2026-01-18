from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from authx import TokenPayload
from fastapi import Depends, HTTPException

from backend.app.core.auth import get_current_payload, get_deps
from backend.app.core.permission_resolver import PermissionSnapshot, resolve_permissions
from backend.app.dependencies import AppDependencies


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
    user = deps.user_store.get_by_user_id(payload.sub)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
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

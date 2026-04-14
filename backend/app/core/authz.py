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


def capability_allowed(
    snapshot: PermissionSnapshot,
    *,
    resource: str,
    action: str,
    target: str | None = None,
) -> bool:
    clean_resource = str(resource or "").strip()
    clean_action = str(action or "").strip()
    if not clean_resource or not clean_action:
        return False

    resource_map = snapshot.capabilities_dict().get(clean_resource, {})
    if not isinstance(resource_map, dict):
        return False
    entry = resource_map.get(clean_action, {})
    if not isinstance(entry, dict):
        return False

    scope = str(entry.get("scope") or "none").strip().lower()
    if scope == "all":
        return True
    if scope != "set":
        return False

    targets = entry.get("targets")
    if not isinstance(targets, list):
        return False

    clean_target = str(target or "").strip()
    normalized_targets = {str(item).strip() for item in targets if isinstance(item, str) and item.strip()}
    if not clean_target:
        return bool(normalized_targets)
    return clean_target in normalized_targets


def assert_capability(
    ctx: AuthContextDep,
    *,
    resource: str,
    action: str,
    target: str | None = None,
    detail: str | None = None,
) -> None:
    if capability_allowed(ctx.snapshot, resource=resource, action=action, target=target):
        return
    raise HTTPException(status_code=403, detail=detail or f"{str(resource or '').strip()}_forbidden")


def require_capability(
    *,
    resource: str,
    action: str,
    target: str | None = None,
    detail: str | None = None,
) -> Any:
    def _dep(ctx: AuthContextDep) -> None:
        assert_capability(ctx, resource=resource, action=action, target=target, detail=detail)

    return Depends(_dep)

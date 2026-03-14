from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.app.core.authz import AuthContextDep, SuperAdminOnly
from backend.services.feature_visibility import resolve_feature_visibility_store

router = APIRouter()


@router.get("/super-admin/feature-visibility")
async def get_feature_visibility(_: SuperAdminOnly, ctx: AuthContextDep) -> dict[str, bool]:
    return resolve_feature_visibility_store(ctx.deps).list_flags()


@router.put("/super-admin/feature-visibility")
async def update_feature_visibility(
    _: SuperAdminOnly,
    ctx: AuthContextDep,
    body: dict[str, Any] | None = None,
) -> dict[str, bool]:
    store = resolve_feature_visibility_store(ctx.deps)
    return store.update_flags(
        body or {},
        actor_user_id=str(getattr(ctx.payload, "sub", "") or ""),
    )

from __future__ import annotations

from fastapi import HTTPException

from backend.services.feature_visibility_store import FeatureVisibilityStore
from backend.services.super_admin import is_super_admin_user


def resolve_feature_visibility_store(deps) -> FeatureVisibilityStore:
    existing = getattr(deps, "feature_visibility_store", None)
    if existing is not None:
        return existing
    kb_store = getattr(deps, "kb_store", None)
    db_path = str(getattr(kb_store, "db_path", "") or "")
    store = FeatureVisibilityStore(db_path=db_path or None)
    try:
        setattr(deps, "feature_visibility_store", store)
    except Exception:
        pass
    return store


def feature_enabled_for_user(*, deps, user, flag_key: str, default: bool = True) -> bool:
    if is_super_admin_user(user):
        return True
    try:
        return bool(resolve_feature_visibility_store(deps).is_enabled(flag_key, default=default))
    except Exception:
        return bool(default)


def assert_feature_visible_or_404(*, deps, user, flag_key: str, default: bool = True) -> None:
    if feature_enabled_for_user(deps=deps, user=user, flag_key=flag_key, default=default):
        return
    raise HTTPException(status_code=404, detail=f"feature_disabled:{flag_key}")

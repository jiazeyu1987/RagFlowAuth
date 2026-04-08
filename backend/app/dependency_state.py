from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.dependency_factory import AppDependencies


def initialize_dependency_state(app: Any, *, base_auth_db_path: str) -> None:
    app.state.base_auth_db_path = base_auth_db_path
    app.state.tenant_deps_cache = {}


def get_base_auth_db_path(app: Any) -> str | None:
    return getattr(getattr(app, "state", None), "base_auth_db_path", None)


def get_tenant_deps_cache(app: Any) -> dict[int, AppDependencies]:
    cache = getattr(getattr(app, "state", None), "tenant_deps_cache", None)
    if isinstance(cache, dict):
        return cache
    cache = {}
    app.state.tenant_deps_cache = cache
    return cache


def get_cached_tenant_dependencies(app: Any, *, company_id: int) -> AppDependencies | None:
    return get_tenant_deps_cache(app).get(company_id)


def cache_tenant_dependencies(
    app: Any,
    *,
    company_id: int,
    deps: AppDependencies,
) -> AppDependencies:
    get_tenant_deps_cache(app)[company_id] = deps
    return deps


def set_global_dependencies(app: Any, deps: AppDependencies) -> AppDependencies:
    app.state.deps = deps
    return deps


def get_global_dependencies(app: Any) -> AppDependencies:
    deps = getattr(getattr(app, "state", None), "deps", None)
    if deps is None:
        raise RuntimeError("app_dependencies_not_initialized")
    return deps

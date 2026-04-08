from __future__ import annotations

from typing import Any, Callable

from backend.app.dependency_factory import AppDependencies, create_app_dependencies
from backend.app.dependency_state import (
    cache_tenant_dependencies,
    get_base_auth_db_path,
    get_cached_tenant_dependencies,
    get_global_dependencies as _get_global_dependencies,
    initialize_dependency_state,
    set_global_dependencies,
)
from backend.database.paths import resolve_auth_db_path
from backend.database.tenant_paths import normalize_company_id, resolve_tenant_auth_db_path


def create_dependencies(
    db_path: str | None = None,
    *,
    operation_approval_control_db_path: str | None = None,
    training_compliance_db_path: str | None = None,
    operation_approval_execution_deps_resolver: Callable[[int | str], AppDependencies] | None = None,
) -> AppDependencies:
    return create_app_dependencies(
        db_path=db_path,
        operation_approval_control_db_path=operation_approval_control_db_path,
        training_compliance_db_path=training_compliance_db_path,
        operation_approval_execution_deps_resolver=operation_approval_execution_deps_resolver,
    )


def initialize_application_dependencies(app: Any) -> AppDependencies:
    base_auth_db_path = str(resolve_auth_db_path())
    initialize_dependency_state(app, base_auth_db_path=base_auth_db_path)
    deps = create_dependencies(
        operation_approval_execution_deps_resolver=lambda company_id: get_tenant_dependencies(
            app,
            company_id=company_id,
        )
    )
    return set_global_dependencies(app, deps)


def get_global_dependencies(app: Any) -> AppDependencies:
    return _get_global_dependencies(app)


def get_tenant_dependencies(app: Any, *, company_id: int | str) -> AppDependencies:
    cid = normalize_company_id(company_id)
    cached = get_cached_tenant_dependencies(app, company_id=cid)
    if cached is not None:
        return cached

    base_db_path = get_base_auth_db_path(app)
    tenant_db_path = resolve_tenant_auth_db_path(company_id=cid, base_db_path=base_db_path)
    deps = create_dependencies(
        db_path=str(tenant_db_path),
        operation_approval_control_db_path=str(base_db_path) if base_db_path is not None else None,
        training_compliance_db_path=str(base_db_path) if base_db_path is not None else None,
        operation_approval_execution_deps_resolver=lambda execution_company_id: get_tenant_dependencies(
            app,
            company_id=execution_company_id,
        ),
    )
    return cache_tenant_dependencies(app, company_id=cid, deps=deps)

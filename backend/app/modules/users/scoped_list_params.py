from __future__ import annotations

from backend.app.modules.users.access import resolve_user_list_scope
from backend.app.modules.users.list_params import build_list_users_kwargs


def build_scoped_list_users_kwargs(
    *,
    q=None,
    role=None,
    group_id=None,
    scoped_company_id=None,
    department_id=None,
    status=None,
    created_from_ms=None,
    created_to_ms=None,
    manager_user_id=None,
    limit: int = 100,
):
    return build_list_users_kwargs(
        q=q,
        role=role,
        group_id=group_id,
        company_id=scoped_company_id,
        department_id=department_id,
        status=status,
        created_from_ms=created_from_ms,
        created_to_ms=created_to_ms,
        manager_user_id=manager_user_id,
        limit=limit,
    )


def build_ctx_scoped_list_users_kwargs(
    ctx,
    *,
    q=None,
    role=None,
    group_id=None,
    company_id=None,
    department_id=None,
    status=None,
    created_from_ms=None,
    created_to_ms=None,
    limit: int = 100,
):
    scoped_company_id, manager_user_id = resolve_user_list_scope(ctx, company_id)
    return build_scoped_list_users_kwargs(
        q=q,
        role=role,
        group_id=group_id,
        scoped_company_id=scoped_company_id,
        department_id=department_id,
        status=status,
        created_from_ms=created_from_ms,
        created_to_ms=created_to_ms,
        manager_user_id=manager_user_id,
        limit=limit,
    )

from __future__ import annotations

from backend.app.modules.users.access import assert_manageable_target_user
from backend.app.modules.users.scoped_list_params import build_ctx_scoped_list_users_kwargs


def list_users_result(
    *,
    ctx,
    service,
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
    return service.list_users(
        **build_ctx_scoped_list_users_kwargs(
            ctx,
            q=q,
            role=role,
            group_id=group_id,
            company_id=company_id,
            department_id=department_id,
            status=status,
            created_from_ms=created_from_ms,
            created_to_ms=created_to_ms,
            limit=limit,
        )
    )


def get_user_result(*, ctx, user_store, service, user_id: str):
    assert_manageable_target_user(ctx, user_store, user_id)
    return service.get_user(user_id=user_id)

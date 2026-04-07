from __future__ import annotations


def build_list_users_kwargs(
    *,
    q=None,
    role=None,
    group_id=None,
    company_id=None,
    department_id=None,
    status=None,
    created_from_ms=None,
    created_to_ms=None,
    manager_user_id=None,
    limit: int = 100,
):
    return {
        "q": q,
        "role": role,
        "group_id": group_id,
        "company_id": company_id,
        "department_id": department_id,
        "status": status,
        "created_from_ms": created_from_ms,
        "created_to_ms": created_to_ms,
        "manager_user_id": manager_user_id,
        "limit": limit,
    }

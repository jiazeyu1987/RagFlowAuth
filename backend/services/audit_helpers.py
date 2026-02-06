from __future__ import annotations

from typing import Any


def actor_fields_from_user(deps: Any, user: Any) -> dict[str, Any]:
    """
    Produce normalized actor fields for audit_events.

    This intentionally duplicates (denormalizes) org/user attributes into audit_events
    to make filtering/reporting simple and stable over time.
    """
    username = getattr(user, "username", None)
    company_id = getattr(user, "company_id", None)
    department_id = getattr(user, "department_id", None)

    company_name = None
    if company_id is not None:
        try:
            c = deps.org_directory_store.get_company(int(company_id))
            company_name = getattr(c, "name", None) if c else None
        except Exception:
            company_name = None

    department_name = None
    if department_id is not None:
        try:
            d = deps.org_directory_store.get_department(int(department_id))
            department_name = getattr(d, "name", None) if d else None
        except Exception:
            department_name = None

    return {
        "actor_username": username,
        "company_id": int(company_id) if company_id is not None else None,
        "company_name": company_name,
        "department_id": int(department_id) if department_id is not None else None,
        "department_name": department_name,
    }


def actor_fields_from_ctx(deps: Any, ctx: Any) -> dict[str, Any]:
    user = getattr(ctx, "user", None)
    if not user:
        return {
            "actor_username": None,
            "company_id": None,
            "company_name": None,
            "department_id": None,
            "department_name": None,
        }
    return actor_fields_from_user(deps, user)


from __future__ import annotations

from fastapi import HTTPException

MANAGEABLE_USER_DETAIL = "sub_admin_can_only_assign_owned_users"


def knowledge_management_manager(ctx):
    manager = getattr(ctx.deps, "knowledge_management_manager", None)
    if manager is None:
        raise HTTPException(status_code=403, detail="admin_required")
    return manager


def chat_management_manager(ctx):
    manager = getattr(ctx.deps, "chat_management_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="chat_management_manager_unavailable")
    return manager


def assert_knowledge_management_access(ctx):
    manager = knowledge_management_manager(ctx)
    try:
        manager.assert_can_manage(ctx.user)
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc
    return manager


def assert_sub_admin_can_manage_users(ctx) -> None:
    assert_knowledge_management_access(ctx)


def resolve_sub_admin_company_id(ctx, requested_company_id: int | None) -> int:
    actor_company_id = getattr(ctx.user, "company_id", None)
    try:
        actor_company_id = int(actor_company_id)
    except Exception as exc:
        raise HTTPException(status_code=403, detail="sub_admin_company_required") from exc

    if requested_company_id is not None and int(requested_company_id) != actor_company_id:
        raise HTTPException(status_code=403, detail="sub_admin_company_scope_violation")
    return actor_company_id


def resolve_user_list_scope(ctx, requested_company_id: int | None) -> tuple[int | None, str | None]:
    if ctx.snapshot.is_admin:
        return requested_company_id, None

    assert_sub_admin_can_manage_users(ctx)
    manager_user_id = str(getattr(ctx.user, "user_id", "") or "").strip() or None
    return resolve_sub_admin_company_id(ctx, requested_company_id), manager_user_id


def assert_sub_admin_owned_viewer(
    ctx,
    target_user,
    *,
    detail: str,
    role_detail: str = "sub_admin_can_only_assign_viewer_groups",
) -> None:
    if not target_user:
        raise HTTPException(status_code=404, detail="user_not_found")
    if str(getattr(target_user, "role", "") or "") != "viewer":
        raise HTTPException(status_code=403, detail=role_detail)

    actor_company_id = resolve_sub_admin_company_id(ctx, None)
    try:
        target_company_id = int(getattr(target_user, "company_id", None))
    except Exception as exc:
        raise HTTPException(status_code=403, detail="sub_admin_company_scope_violation") from exc
    if target_company_id != actor_company_id:
        raise HTTPException(status_code=403, detail="sub_admin_company_scope_violation")

    if str(getattr(target_user, "manager_user_id", "") or "") != str(getattr(ctx.user, "user_id", "") or ""):
        raise HTTPException(status_code=403, detail=detail)


def get_manageable_target_user(ctx, user_store, user_id: str, *, detail: str, role_detail: str | None = None):
    target_user = user_store.get_by_user_id(user_id)
    assert_sub_admin_owned_viewer(
        ctx,
        target_user,
        detail=detail,
        role_detail=role_detail or "sub_admin_can_only_assign_viewer_groups",
    )
    return target_user


def assert_manageable_target_user(ctx, user_store, user_id: str) -> None:
    if ctx.snapshot.is_admin:
        return
    get_manageable_target_user(
        ctx,
        user_store,
        user_id,
        detail=MANAGEABLE_USER_DETAIL,
    )


def resolve_password_reset_target(ctx, user_store, user_id: str):
    if str(user_id) == str(getattr(ctx.user, "user_id", "") or ""):
        return ctx.user
    return user_store.get_by_user_id(user_id)


def assert_can_reset_password(ctx, target_user) -> None:
    if ctx.snapshot.is_admin:
        return
    if str(getattr(ctx.user, "role", "") or "") != "sub_admin":
        raise HTTPException(status_code=403, detail="admin_required")

    actor_user_id = str(getattr(ctx.user, "user_id", "") or "")
    target_user_id = str(getattr(target_user, "user_id", "") or "")
    if target_user_id == actor_user_id:
        return

    assert_sub_admin_owned_viewer(
        ctx,
        target_user,
        detail="sub_admin_can_only_reset_password_for_owned_users",
        role_detail="sub_admin_can_only_reset_password_for_owned_users",
    )

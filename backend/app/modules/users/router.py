from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.app.core.auth import get_deps, get_global_deps
from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.dependencies import AppDependencies
from backend.app.modules.permission_groups.service import PermissionGroupsService
from backend.app.modules.users.repo import UsersRepo
from backend.app.modules.users.service import UsersService
from backend.models.user import UserCreate, UserResponse, UserUpdate
from backend.services.audit_helpers import actor_fields_from_user


class ResetPasswordRequest(BaseModel):
    new_password: str


router = APIRouter()


def get_service(
    global_deps: AppDependencies = Depends(get_global_deps),
    scoped_deps: AppDependencies = Depends(get_deps),
) -> UsersService:
    return UsersService(
        UsersRepo(
            global_deps,
            permission_group_store=getattr(scoped_deps, "permission_group_store", None),
        )
    )


def _assert_sub_admin_can_manage_users(ctx: AuthContextDep) -> None:
    manager = getattr(ctx.deps, "knowledge_management_manager", None)
    if manager is None:
        raise HTTPException(status_code=403, detail="admin_required")
    try:
        manager.assert_can_manage(ctx.user)
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc


def _resolve_sub_admin_company_id(ctx: AuthContextDep, requested_company_id: int | None) -> int:
    actor_company_id = getattr(ctx.user, "company_id", None)
    try:
        actor_company_id = int(actor_company_id)
    except Exception as exc:
        raise HTTPException(status_code=403, detail="sub_admin_company_required") from exc

    if requested_company_id is not None and int(requested_company_id) != actor_company_id:
        raise HTTPException(status_code=403, detail="sub_admin_company_scope_violation")
    return actor_company_id


def _assert_sub_admin_owned_viewer(
    ctx: AuthContextDep,
    target_user,
    *,
    detail: str,
    role_detail: str = "sub_admin_can_only_assign_viewer_groups",
) -> None:
    if not target_user:
        raise HTTPException(status_code=404, detail="user_not_found")
    if str(getattr(target_user, "role", "") or "") != "viewer":
        raise HTTPException(status_code=403, detail=role_detail)

    actor_company_id = _resolve_sub_admin_company_id(ctx, None)
    try:
        target_company_id = int(getattr(target_user, "company_id", None))
    except Exception as exc:
        raise HTTPException(status_code=403, detail="sub_admin_company_scope_violation") from exc
    if target_company_id != actor_company_id:
        raise HTTPException(status_code=403, detail="sub_admin_company_scope_violation")

    if str(getattr(target_user, "manager_user_id", "") or "") != str(getattr(ctx.user, "user_id", "") or ""):
        raise HTTPException(status_code=403, detail=detail)


def _assert_can_reset_password(ctx: AuthContextDep, target_user) -> None:
    if ctx.snapshot.is_admin:
        return
    if str(getattr(ctx.user, "role", "") or "") != "sub_admin":
        raise HTTPException(status_code=403, detail="admin_required")

    actor_user_id = str(getattr(ctx.user, "user_id", "") or "")
    target_user_id = str(getattr(target_user, "user_id", "") or "")
    if target_user_id == actor_user_id:
        return

    _assert_sub_admin_owned_viewer(
        ctx,
        target_user,
        detail="sub_admin_can_only_reset_password_for_owned_users",
        role_detail="sub_admin_can_only_reset_password_for_owned_users",
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    ctx: AuthContextDep,
    service: UsersService = Depends(get_service),
    q: Optional[str] = None,
    role: Optional[str] = None,
    group_id: Optional[int] = None,
    company_id: Optional[int] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    created_from_ms: Optional[int] = None,
    created_to_ms: Optional[int] = None,
    limit: int = 100,
):
    manager_user_id: str | None = None
    if not ctx.snapshot.is_admin:
        _assert_sub_admin_can_manage_users(ctx)
        company_id = _resolve_sub_admin_company_id(ctx, company_id)
        manager_user_id = str(getattr(ctx.user, "user_id", "") or "").strip() or None
    return service.list_users(
        q=q,
        role=role,
        group_id=group_id,
        company_id=company_id,
        department_id=department_id,
        status=status,
        created_from_ms=created_from_ms,
        created_to_ms=created_to_ms,
        manager_user_id=manager_user_id,
        limit=limit,
    )


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    payload: AdminOnly,
    service: UsersService = Depends(get_service),
):
    return service.create_user(user_data=user_data, created_by=payload.sub)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    ctx: AuthContextDep,
    global_deps: AppDependencies = Depends(get_global_deps),
    service: UsersService = Depends(get_service),
):
    if not ctx.snapshot.is_admin:
        _assert_sub_admin_can_manage_users(ctx)
        target_user = global_deps.user_store.get_by_user_id(user_id)
        _assert_sub_admin_owned_viewer(ctx, target_user, detail="sub_admin_can_only_assign_owned_users")
    return service.get_user(user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    ctx: AuthContextDep,
    global_deps: AppDependencies = Depends(get_global_deps),
    service: UsersService = Depends(get_service),
):
    if ctx.snapshot.is_admin:
        return service.update_user(user_id=user_id, user_data=user_data)

    fields_set = set(getattr(user_data, "model_fields_set", set()) or set())
    allowed_fields = {"group_id", "group_ids"}
    disallowed = [field for field in fields_set if field not in allowed_fields]
    if disallowed:
        manager = getattr(ctx.deps, "knowledge_management_manager", None)
        if manager is None:
            raise HTTPException(status_code=403, detail="admin_required")
        try:
            manager.assert_can_manage(ctx.user)
        except Exception as exc:
            raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc
        raise HTTPException(status_code=403, detail="sub_admin_group_assignment_only")

    target_user = global_deps.user_store.get_by_user_id(user_id)
    _assert_sub_admin_owned_viewer(ctx, target_user, detail="sub_admin_can_only_assign_owned_users")

    target_group_ids = user_data.group_ids
    if target_group_ids is None and user_data.group_id is not None:
        target_group_ids = [user_data.group_id]
    if target_group_ids is not None:
        permission_group_service = PermissionGroupsService(ctx.deps)
        try:
            permission_group_service.validate_group_ids_manageable(
                user=ctx.user,
                group_ids=[int(group_id) for group_id in target_group_ids],
            )
        except HTTPException:
            raise
        manager = getattr(ctx.deps, "knowledge_management_manager", None)
        if manager is None:
            raise HTTPException(status_code=403, detail="admin_required")
        try:
            manager.validate_permission_group_ids(
                user=ctx.user,
                group_ids=[int(group_id) for group_id in target_group_ids],
                permission_group_store=ctx.deps.permission_group_store,
            )
        except Exception as exc:
            raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc
        chat_manager = getattr(ctx.deps, "chat_management_manager", None)
        if chat_manager is None:
            raise HTTPException(status_code=500, detail="chat_management_manager_unavailable")
        try:
            chat_manager.validate_permission_group_ids(
                user=ctx.user,
                group_ids=[int(group_id) for group_id in target_group_ids],
                permission_group_store=ctx.deps.permission_group_store,
            )
        except Exception as exc:
            raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc
    return service.update_user(user_id=user_id, user_data=user_data)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    _: AdminOnly,
    service: UsersService = Depends(get_service),
):
    service.delete_user(user_id)
    return {"message": "用户已删除"}


@router.put("/{user_id}/password")
async def reset_password(
    user_id: str,
    body: ResetPasswordRequest,
    ctx: AuthContextDep,
    request: Request,
    deps: AppDependencies = Depends(get_global_deps),
    service: UsersService = Depends(get_service),
):
    target_user = ctx.user if str(user_id) == str(getattr(ctx.user, "user_id", "") or "") else deps.user_store.get_by_user_id(user_id)
    _assert_can_reset_password(ctx, target_user)

    service.reset_password(user_id, body.new_password)

    actor_user = ctx.user
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    client_ip = getattr(getattr(request, "client", None), "host", None)
    deps.audit_log_manager.log_event(
        action="user_password_reset",
        actor=str(getattr(actor_user, "user_id", "") or ""),
        source="users",
        resource_type="user",
        resource_id=str(user_id),
        event_type="update",
        before={"password_changed": False},
        after={"password_changed": True},
        request_id=request_id,
        client_ip=client_ip,
        meta={
            "target_user_id": user_id,
            "target_username": getattr(target_user, "username", None),
        },
        **actor_fields_from_user(deps, actor_user),
    )
    return {"message": "密码已重置"}

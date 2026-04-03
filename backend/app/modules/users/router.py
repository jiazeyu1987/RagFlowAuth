from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.app.core.auth import get_deps
from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.dependencies import AppDependencies
from backend.app.modules.users.repo import UsersRepo
from backend.app.modules.users.service import UsersService
from backend.models.user import UserCreate, UserResponse, UserUpdate
from backend.services.audit_helpers import actor_fields_from_user


class ResetPasswordRequest(BaseModel):
    new_password: str


router = APIRouter()


def get_service(deps: AppDependencies = Depends(get_deps)) -> UsersService:
    return UsersService(UsersRepo(deps))


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
    if not ctx.snapshot.is_admin:
        manager = getattr(ctx.deps, "knowledge_management_manager", None)
        if manager is None:
            raise HTTPException(status_code=403, detail="admin_required")
        try:
            manager.assert_can_manage(ctx.user)
        except Exception as exc:
            raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc
    return service.list_users(
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
    service: UsersService = Depends(get_service),
):
    if not ctx.snapshot.is_admin:
        manager = getattr(ctx.deps, "knowledge_management_manager", None)
        if manager is None:
            raise HTTPException(status_code=403, detail="admin_required")
        try:
            manager.assert_can_manage(ctx.user)
        except Exception as exc:
            raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc
    return service.get_user(user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    ctx: AuthContextDep,
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

    target_user = ctx.deps.user_store.get_by_user_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="user_not_found")
    if str(getattr(target_user, "role", "") or "") != "viewer":
        raise HTTPException(status_code=403, detail="sub_admin_can_only_assign_viewer_groups")
    if str(getattr(target_user, "manager_user_id", "") or "") != str(getattr(ctx.user, "user_id", "") or ""):
        raise HTTPException(status_code=403, detail="sub_admin_can_only_assign_owned_users")

    target_group_ids = user_data.group_ids
    if target_group_ids is None and user_data.group_id is not None:
        target_group_ids = [user_data.group_id]
    if target_group_ids is not None:
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
    admin_payload: AdminOnly,
    request: Request,
    deps: AppDependencies = Depends(get_deps),
    service: UsersService = Depends(get_service),
):
    service.reset_password(user_id, body.new_password)

    actor_user = deps.user_store.get_by_user_id(admin_payload.sub)
    if not actor_user:
        raise HTTPException(status_code=401, detail="actor_user_not_found")
    target_user = deps.user_store.get_by_user_id(user_id)
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    client_ip = getattr(getattr(request, "client", None), "host", None)
    deps.audit_log_manager.log_event(
        action="user_password_reset",
        actor=admin_payload.sub,
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

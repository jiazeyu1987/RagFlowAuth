from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.app.core.auth import get_deps
from backend.app.core.authz import AuthContextDep
from backend.app.core.permdbg import permdbg
from backend.app.core.permission_resolver import ResourceScope
from backend.core.security import auth
from backend.app.dependencies import AppDependencies
from backend.models.auth import LoginRequest, TokenResponse, ChangePasswordRequest
from backend.services.user_store import hash_password
from backend.services.users import validate_password_requirements
from backend.services.audit_helpers import actor_fields_from_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    response: Response,
    deps: AppDependencies = Depends(get_deps),
):
    user = deps.user_store.get_by_username(credentials.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if hash_password(credentials.password) != user.password_hash:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if user.status != "active":
        raise HTTPException(status_code=403, detail="账户已被禁用")

    scopes: list[str] = []

    access_token = auth.create_access_token(uid=user.user_id, scopes=scopes)
    refresh_token = auth.create_refresh_token(uid=user.user_id)
    auth.set_access_cookies(access_token, response)
    auth.set_refresh_cookies(refresh_token, response)

    deps.user_store.update_last_login(user.user_id)
    audit = getattr(deps, "audit_log_store", None)
    if audit:
        try:
            audit.log_event(
                action="auth_login",
                actor=user.user_id,
                source="auth",
                meta={"username": user.username},
                **actor_fields_from_user(deps, user),
            )
        except Exception:
            pass

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        scopes=scopes,
    )


@router.post("/refresh")
async def refresh_token(request: Request):
    try:
        refresh_token_value: str | None = None
        try:
            refresh_token_value = await auth.get_refresh_token_from_request(request)
        except Exception:
            refresh_token_value = None

        # Frontend sends refresh token via Authorization header.
        if not refresh_token_value:
            auth_header = request.headers.get("Authorization") or ""
            if auth_header.startswith("Bearer "):
                refresh_token_value = auth_header.split(" ", 1)[1].strip() or None

        if not refresh_token_value:
            raise HTTPException(status_code=401, detail="缺少刷新令牌")

        payload = auth.verify_token(refresh_token_value, verify_type=True)

        deps = request.app.state.deps
        user = deps.user_store.get_by_user_id(payload.sub)
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")

        if user.status != "active":
            raise HTTPException(status_code=403, detail="账户已被禁用")

        scopes: list[str] = []
        access_token = auth.create_access_token(uid=payload.sub, scopes=scopes)
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"刷新令牌无效: {str(e)}")


@router.post("/logout")
async def logout(request: Request, response: Response, deps: AppDependencies = Depends(get_deps)):
    actor = None
    try:
        token = await auth.get_access_token_from_request(request)
        payload = auth.verify_token(token, verify_type=True)
        actor = payload.sub
    except Exception:
        actor = None

    audit = getattr(deps, "audit_log_store", None)
    if audit and actor:
        try:
            user = deps.user_store.get_by_user_id(actor)
            audit.log_event(
                action="auth_logout",
                actor=actor,
                source="auth",
                **(actor_fields_from_user(deps, user) if user else {}),
            )
        except Exception:
            pass
    auth.unset_cookies(response)
    return {"message": "登出成功"}


@router.get("/me")
async def get_current_user(
    ctx: AuthContextDep,
):
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    permissions = snapshot.permissions_dict()

    # Debug: trace where KB visibility comes from (permission groups + per-user grants).
    try:
        group_ids = list(user.group_ids or [])
        group_kbs: list[str] = []
        for gid in group_ids:
            group = deps.permission_group_store.get_group(gid)
            if not group:
                continue
            for ref in (group.get("accessible_kbs") or []):
                if isinstance(ref, str) and ref:
                    group_kbs.append(ref)
        permdbg(
            "auth.me.snapshot",
            user=user.username,
            role=user.role,
            group_ids=group_ids,
            kb_scope=snapshot.kb_scope,
            kb_refs=sorted(list(snapshot.kb_names))[:50],
            group_kbs=sorted(set([x for x in group_kbs if isinstance(x, str) and x]))[:50],
        )
    except Exception:
        # Best-effort debug only.
        pass

    if snapshot.kb_scope == ResourceScope.ALL:
        datasets = deps.ragflow_service.list_all_datasets() if hasattr(deps.ragflow_service, "list_all_datasets") else deps.ragflow_service.list_datasets()
        accessible_kb_ids_set: set[str] = {ds.get("id") for ds in datasets or [] if isinstance(ds, dict) and ds.get("id")}
        accessible_kb_names_set: set[str] = {ds.get("name") for ds in datasets or [] if isinstance(ds, dict) and ds.get("name")}
    else:
        accessible_kb_ids_set = set(deps.ragflow_service.normalize_dataset_ids(snapshot.kb_names)) if hasattr(deps.ragflow_service, "normalize_dataset_ids") else set()
        accessible_kb_names_set = set(deps.ragflow_service.resolve_dataset_names(snapshot.kb_names)) if hasattr(deps.ragflow_service, "resolve_dataset_names") else set(snapshot.kb_names)

    if snapshot.chat_scope == ResourceScope.ALL:
        accessible_chats_set: set[str] = set(deps.ragflow_chat_service.list_all_chat_ids())
    else:
        accessible_chats_set = set(snapshot.chat_ids)

    try:
        permdbg(
            "auth.me.effective",
            accessible_kbs=sorted(accessible_kb_names_set)[:50],
            accessible_kb_ids=sorted(accessible_kb_ids_set)[:50],
            accessible_chats_count=len(accessible_chats_set),
        )
    except Exception:
        pass

    permission_groups_list: list[dict] = []

    group_ids = list(user.group_ids or [])
    if not group_ids and user.group_id is not None:
        group_ids = [user.group_id]

    if group_ids:
        for group_id in group_ids:
            group = deps.permission_group_store.get_group(group_id)
            if not group:
                continue

            permission_groups_list.append({"group_id": group_id, "group_name": group.get("group_name", "")})

    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "group_id": user.group_id,
        "group_ids": user.group_ids,
        "permission_groups": permission_groups_list,
        "scopes": [],
        "permissions": permissions,
        # Legacy field: dataset names (for display).
        "accessible_kbs": sorted(accessible_kb_names_set),
        # New field: dataset ids (for API operations / stage-3 migration).
        "accessible_kb_ids": sorted(accessible_kb_ids_set),
        "accessible_chats": sorted(accessible_chats_set),
    }


@router.put("/password")
async def change_password(
    request_data: ChangePasswordRequest,
    ctx: AuthContextDep,
):
    """
    Change password for authenticated user.

    Requires:
    - Correct old password
    - New password meets validation requirements
    """
    deps = ctx.deps
    user = ctx.user

    # Verify old password
    if hash_password(request_data.old_password) != user.password_hash:
        raise HTTPException(status_code=400, detail="旧密码错误")

    # Validate new password requirements
    if not validate_password_requirements(
        password=request_data.new_password,
        old_password=request_data.old_password,
    ):
        # Check specific validation error for better error messages
        if len(request_data.new_password) < 6:
            raise HTTPException(status_code=400, detail="密码不符合要求：密码长度至少6个字符")
        if request_data.new_password == request_data.old_password:
            raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")
        raise HTTPException(status_code=400, detail="密码不符合要求：必须包含字母和数字，且不能使用常见密码")

    # Update password
    deps.user_store.update_password(user.user_id, request_data.new_password)

    logger.info(f"Password changed for user {user.username}")

    return {"message": "密码修改成功"}

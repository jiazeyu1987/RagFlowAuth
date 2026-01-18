from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.app.core.auth import get_deps
from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import ResourceScope
from backend.core.security import auth
from backend.app.dependencies import AppDependencies
from backend.models.auth import LoginRequest, TokenResponse
from backend.services.user_store import hash_password

router = APIRouter()
logger = logging.getLogger(__name__)
perm_logger = logging.getLogger("uvicorn.error")


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

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        scopes=scopes,
    )


@router.post("/refresh")
async def refresh_token(request: Request):
    try:
        refresh_token_value = await auth.get_refresh_token_from_request(request)
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
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"刷新令牌无效: {str(e)}")


@router.post("/logout")
async def logout(response: Response):
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
        user_kbs = deps.user_kb_permission_store.get_user_kbs(user.user_id) or []
        perm_logger.info(
            "[PERMDBG] /api/auth/me user=%s role=%s group_ids=%s kb_scope=%s kb_refs=%s group_kbs=%s user_kbs=%s",
            user.username,
            user.role,
            group_ids,
            snapshot.kb_scope,
            sorted(list(snapshot.kb_names))[:50],
            sorted(set([x for x in group_kbs if isinstance(x, str) and x]))[:50],
            sorted(set([x for x in user_kbs if isinstance(x, str) and x]))[:50],
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
        perm_logger.info(
            "[PERMDBG] /api/auth/me effective accessible_kbs=%s accessible_kb_ids=%s accessible_chats_count=%s",
            sorted(accessible_kb_names_set)[:50],
            sorted(accessible_kb_ids_set)[:50],
            len(accessible_chats_set),
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

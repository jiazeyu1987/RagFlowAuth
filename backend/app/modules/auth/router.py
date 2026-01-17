from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.auth import AuthRequired, get_deps
from app.core.permission_resolver import ResourceScope, list_all_kb_names, resolve_permissions
from core.security import auth
from core.scopes import get_scopes_for_role
from dependencies import AppDependencies
from models.auth import LoginRequest, TokenResponse
from services.user_store import hash_password

router = APIRouter()


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

    scopes = get_scopes_for_role(user.role)

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

        scopes = get_scopes_for_role(user.role)
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
    payload: AuthRequired,
    deps: AppDependencies = Depends(get_deps),
):
    user = deps.user_store.get_by_user_id(payload.sub)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    snapshot = resolve_permissions(deps, user)
    permissions = snapshot.permissions_dict()

    if snapshot.kb_scope == ResourceScope.ALL:
        accessible_kbs_set: set[str] = set(list_all_kb_names(deps))
    else:
        accessible_kbs_set = set(snapshot.kb_names)

    if snapshot.chat_scope == ResourceScope.ALL:
        accessible_chats_set: set[str] = set()
    else:
        accessible_chats_set = set(snapshot.chat_ids)
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
        "scopes": get_scopes_for_role(user.role),
        "permissions": permissions,
        "accessible_kbs": sorted(accessible_kbs_set),
        "accessible_chats": sorted(accessible_chats_set),
    }

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.auth import get_deps
from backend.app.core.authz import AuthContextDep
from backend.app.core.authz import AdminOnly
from backend.app.dependencies import AppDependencies

from backend.app.modules.user_chat_permissions.repo import UserChatPermissionsRepo
from backend.app.modules.user_chat_permissions.schemas import BatchGrantChatsRequest, ChatListResponse
from backend.app.modules.user_chat_permissions.service import UserChatPermissionsService


router = APIRouter()


def get_service(deps: AppDependencies = Depends(get_deps)) -> UserChatPermissionsService:
    return UserChatPermissionsService(UserChatPermissionsRepo(deps))


@router.get("/users/{user_id}/chats", response_model=ChatListResponse)
async def get_user_chats(
    user_id: str,
    _: AdminOnly,
    service: UserChatPermissionsService = Depends(get_service),
):
    return ChatListResponse(chat_ids=service.get_user_chats_admin(user_id))


@router.post("/users/{user_id}/chats/{chat_id}", status_code=201)
async def grant_chat_access(
    user_id: str,
    chat_id: str,
    payload: AdminOnly,
    service: UserChatPermissionsService = Depends(get_service),
):
    username = service.grant_chat_access_admin(user_id=user_id, chat_id=chat_id, granted_by=payload.sub)
    return {"message": f"已授予用户 {username} 访问聊天助手 '{chat_id}' 的权限"}


@router.delete("/users/{user_id}/chats/{chat_id}")
async def revoke_chat_access(
    user_id: str,
    chat_id: str,
    _: AdminOnly,
    service: UserChatPermissionsService = Depends(get_service),
):
    username = service.revoke_chat_access_admin(user_id=user_id, chat_id=chat_id)
    return {"message": f"已撤销用户 {username} 访问聊天助手 '{chat_id}' 的权限"}


@router.get("/me/chats", response_model=ChatListResponse)
async def get_my_chats(
    ctx: AuthContextDep,
):
    if ctx.snapshot.is_admin:
        return ChatListResponse(chat_ids=ctx.deps.ragflow_chat_service.list_all_chat_ids())
    return ChatListResponse(chat_ids=sorted(ctx.snapshot.chat_ids))


@router.post("/users/batch-grant-chats")
async def batch_grant_chats(
    request_data: BatchGrantChatsRequest,
    payload: AdminOnly,
    service: UserChatPermissionsService = Depends(get_service),
):
    granted, revoked = service.batch_grant_chats_admin(
        user_ids=request_data.user_ids,
        chat_ids=request_data.chat_ids,
        granted_by=payload.sub,
    )
    return {
        "message": f"已为 {len(request_data.user_ids)} 个用户配置 {len(request_data.chat_ids)} 个聊天助手的权限（删除了 {revoked} 个旧权限）",
        "total_permissions": granted,
        "revoked_permissions": revoked,
    }

from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import logging
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import ResourceScope, normalize_accessible_chat_ids


router = APIRouter()
logger = logging.getLogger(__name__)


def _assert_chat_access(snapshot, chat_id: Optional[str] = None) -> set[str]:
    if snapshot.chat_scope == ResourceScope.ALL:
        return set()
    if snapshot.chat_scope == ResourceScope.NONE:
        raise HTTPException(status_code=403, detail="无权访问该聊天助手")

    allowed_raw_ids = normalize_accessible_chat_ids(snapshot.chat_ids)
    if chat_id is not None and chat_id not in allowed_raw_ids:
        raise HTTPException(status_code=403, detail="无权访问该聊天助手")
    return allowed_raw_ids


class ChatCompletionRequest(BaseModel):
    """Chat completion request model"""
    question: str
    stream: bool = True
    session_id: Optional[str] = None


class DeleteSessionsRequest(BaseModel):
    """Delete sessions request model"""
    ids: Optional[list[str]] = None


@router.get("/chats")
async def list_chats(
    ctx: AuthContextDep,
    page: int = 1,
    page_size: int = 30,
    orderby: str = "create_time",
    desc: bool = True,
    name: Optional[str] = None,
    chat_id: Optional[str] = None,
):
    """
    列出用户有权限访问的聊天助手（基于权限组）

    权限规则：
    - 管理员：可以看到所有聊天助手
    - 其他角色：根据权限组的accessible_chats配置
    """
    deps = ctx.deps
    snapshot = ctx.snapshot
    # 获取所有聊天助手
    all_chats = deps.ragflow_chat_service.list_chats(
        page=page,
        page_size=page_size,
        orderby=orderby,
        desc=desc,
        name=name,
        chat_id=chat_id
    )

    # 非管理员用户根据 resolver 过滤
    if not isinstance(all_chats, list):
        logger.error("ragflow_chat_service.list_chats returned non-list: %s", type(all_chats).__name__)
        all_chats = []

    if not snapshot.is_admin:
        if snapshot.chat_scope == ResourceScope.NONE:
            return {"chats": [], "count": 0}
        allowed_ids = normalize_accessible_chat_ids(snapshot.chat_ids)
        all_chats = [chat for chat in all_chats if isinstance(chat, dict) and chat.get("id") in allowed_ids]

    return {
        "chats": all_chats,
        "count": len(all_chats)
    }


@router.get("/chats/my")
async def get_my_chats(
    ctx: AuthContextDep,
):
    """
    获取当前用户有权限访问的聊天助手列表（基于权限组）

    Note:
    - 前端 AI 对话页目前只支持 chats，不支持 agents；否则会把 agent_id 当 chat_id 调用错误的接口。
    """
    deps = ctx.deps
    snapshot = ctx.snapshot
    # 获取所有聊天助手
    all_chats = deps.ragflow_chat_service.list_chats(page_size=1000)

    if not isinstance(all_chats, list):
        logger.error("ragflow_chat_service.list_chats returned non-list: %s", type(all_chats).__name__)
        all_chats = []

    # 获取用户的可访问聊天体列表（从 resolver）
    if snapshot.is_admin:
        allowed_ids = None
    else:
        if snapshot.chat_scope == ResourceScope.NONE:
            return {"chats": [], "count": 0}
        allowed_ids = normalize_accessible_chat_ids(snapshot.chat_ids)

    if allowed_ids is None:
        filtered_chats = all_chats
    else:
        filtered_chats = [chat for chat in all_chats if chat.get("id") in allowed_ids]

    return {
        "chats": filtered_chats,
        "count": len(filtered_chats)
    }


@router.get("/chats/{chat_id}")
async def get_chat(
    chat_id: str,
    ctx: AuthContextDep,
):
    """获取单个聊天助手详情（基于权限组）"""
    deps = ctx.deps
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        _assert_chat_access(snapshot, chat_id=chat_id)

    chat = deps.ragflow_chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="聊天助手不存在")

    return chat


@router.post("/chats/{chat_id}/sessions")
async def create_session(
    chat_id: str,
    ctx: AuthContextDep,
    name: str = "新会话",
    user_id: Optional[str] = None,
):
    """
    创建聊天会话

    权限规则：
    - 用户必须有该聊天助手的权限
    """
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        _assert_chat_access(snapshot, chat_id=chat_id)

    # 创建会话（使用当前用户的user_id）
    session = deps.ragflow_chat_service.create_session(
        chat_id=chat_id,
        name=name,
        user_id=user.user_id
    )

    if not session:
        raise HTTPException(status_code=500, detail="创建会话失败")

    return session


@router.get("/chats/{chat_id}/sessions")
async def list_sessions(
    chat_id: str,
    ctx: AuthContextDep,
):
    """
    列出聊天助手的所有会话

    权限规则：
    - 用户必须有该聊天助手的权限
    - 只能看到自己的会话
    - 直接从 RAGFlow API 获取,包含完整的 messages 数据
    """
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        _assert_chat_access(snapshot, chat_id=chat_id)

    # 从 RAGFlow API 获取当前用户的会话列表（包含 messages）
    sessions = deps.ragflow_chat_service.list_sessions(
        chat_id=chat_id,
        user_id=user.user_id
    )

    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@router.post("/chats/{chat_id}/completions")
async def chat_completion(
    chat_id: str,
    request: Request,
    body: ChatCompletionRequest,
    ctx: AuthContextDep,
):
    """
    与聊天助手对话（流式）

    权限规则：
    - 用户必须有该聊天助手的权限
    """
    logger.info(f"[CHAT] chat_id={chat_id}, question={body.question[:50]}..., session_id={body.session_id}")

    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        try:
            _assert_chat_access(snapshot, chat_id=chat_id)
        except HTTPException:
            logger.warning(f"[CHAT] User {user.username} has no permission for chat {chat_id}")
            raise

    if not body.question:
        logger.warning("[CHAT] Empty question received")
        raise HTTPException(status_code=400, detail="问题不能为空")

    async def generate():
        try:
            logger.info(f"[CHAT] Starting chat stream for session {body.session_id}")
            async for chunk in deps.ragflow_chat_service.chat(
                chat_id=chat_id,
                question=body.question,
                stream=body.stream,
                session_id=body.session_id,
                user_id=user.user_id
            ):
                # SSE格式
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"[CHAT] Error during chat: {e}", exc_info=True)
            error_chunk = {"code": -1, "message": str(e)}
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.delete("/chats/{chat_id}/sessions")
async def delete_sessions(
    chat_id: str,
    ctx: AuthContextDep,
    body: DeleteSessionsRequest = None,
):
    """
    删除聊天会话

    权限规则：
    - 用户必须有该聊天助手的权限
    - 只能删除自己的会话（管理员可以删除所有）
    """
    # Extract session_ids from request body
    session_ids = body.ids if body else None

    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        _assert_chat_access(snapshot, chat_id=chat_id)

    # 非管理员用户：检查会话所有权
    if not snapshot.is_admin and session_ids:
        for session_id in session_ids:
            owns_session = deps.chat_session_store.check_ownership(
                session_id=session_id,
                chat_id=chat_id,
                user_id=user.user_id
            )
            if not owns_session:
                raise HTTPException(status_code=403, detail=f"无权删除会话 {session_id}")

    # 删除会话（RAGFlow + 本地数据库）
    success = deps.ragflow_chat_service.delete_sessions(
        chat_id=chat_id,
        session_ids=session_ids,
        user_id=user.user_id  # 传递给本地数据库标记删除者
    )

    if not success:
        raise HTTPException(status_code=500, detail="删除会话失败")

    return {"message": "会话已删除"}

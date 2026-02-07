from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import logging
import asyncio
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import ResourceScope, allowed_dataset_ids, normalize_accessible_chat_ids
from backend.services.chat_message_sources_store import content_hash_hex


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


class RenameSessionRequest(BaseModel):
    """Rename a chat session (stored locally for display)."""
    name: str


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

    # Overlay session name from local store (supports user rename).
    try:
        local_sessions = deps.chat_session_store.get_user_sessions(chat_id=chat_id, user_id=user.user_id)
        name_map = {str(s.get("id")): str(s.get("name") or "") for s in (local_sessions or [])}
        for s in sessions or []:
            sid = str(s.get("id") or "")
            local_name = (name_map.get(sid) or "").strip()
            if local_name:
                s["name"] = local_name
    except Exception:
        logger.exception("Failed to overlay session names from local store")

    # Restore assistant `sources` from local sqlite (auth.db) so history survives backup/restore.
    # RAGFlow session history does not include our `sources` payload.
    try:
        src_store = getattr(deps, "chat_message_sources_store", None)
        if src_store and isinstance(sessions, list):
            for s in sessions:
                if not isinstance(s, dict):
                    continue
                sid = str(s.get("id") or "")
                msgs = s.get("messages")
                if not sid or not isinstance(msgs, list):
                    continue

                hashes: list[str] = []
                idx_to_hash: dict[int, str] = {}
                for i, m in enumerate(msgs):
                    if not isinstance(m, dict):
                        continue
                    if str(m.get("role") or "").lower() != "assistant":
                        continue
                    existing = m.get("sources")
                    if isinstance(existing, list) and len(existing) > 0:
                        continue
                    content = m.get("content") or m.get("answer") or ""
                    h = content_hash_hex(str(content or ""))
                    hashes.append(h)
                    idx_to_hash[i] = h

                if not hashes:
                    continue

                sources_map = src_store.get_sources_map(chat_id=chat_id, session_id=sid, content_hashes=hashes)
                if not sources_map:
                    continue
                for i, h in idx_to_hash.items():
                    srcs = sources_map.get(h)
                    if isinstance(srcs, list) and len(srcs) > 0:
                        try:
                            msgs[i]["sources"] = srcs
                        except Exception:
                            pass
    except Exception:
        logger.exception("Failed to restore chat sources from sqlite")

    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@router.put("/chats/{chat_id}/sessions/{session_id}")
async def rename_session(
    chat_id: str,
    session_id: str,
    ctx: AuthContextDep,
    body: RenameSessionRequest = Body(...),
):
    """
    Rename a chat session for easier recognition.

    Notes:
    - Name is stored in RagflowAuth local DB and used to override display name.
    - This does not require RAGFlow to support rename endpoint.
    """
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        _assert_chat_access(snapshot, chat_id=chat_id)

    new_name = str((body.name if body else "") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="name_required")
    if len(new_name) > 120:
        raise HTTPException(status_code=400, detail="name_too_long")

    # Non-admin can only rename own sessions.
    if not snapshot.is_admin:
        owns_session = deps.chat_session_store.check_ownership(session_id=session_id, chat_id=chat_id, user_id=user.user_id)
        if not owns_session:
            raise HTTPException(status_code=403, detail=f"无权重命名会话 {session_id}")

    ok = deps.chat_session_store.set_session_name(
        session_id=session_id,
        chat_id=chat_id,
        user_id=user.user_id,
        name=new_name,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="rename_failed")

    return {"id": session_id, "name": new_name}


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
        sources_task: asyncio.Task | None = None
        try:
            logger.info(f"[CHAT] Starting chat stream for session {body.session_id}")

            built_sources: list[dict] = []
            effective_session_id = str(body.session_id or "").strip() or None
            sources_sent = False
            assistant_text_for_hash = ""

            # Build retrieval sources in the background so we never block streaming answers.
            def _build_sources_sync() -> list[dict]:
                try:
                    ragflow_service = getattr(deps, "ragflow_service", None)
                    if ragflow_service is None:
                        return []
                    all_datasets = ragflow_service.list_datasets() or []
                    dataset_ids = allowed_dataset_ids(snapshot, all_datasets)
                    if not dataset_ids:
                        return []

                    dataset_candidates: list[str] = []
                    try:
                        for ds_id in dataset_ids:
                            try:
                                name = ragflow_service.resolve_dataset_name(ds_id)
                            except Exception:
                                name = None
                            dataset_candidates.append(name or ds_id)
                    except Exception:
                        dataset_candidates = []

                    retrieval = deps.ragflow_chat_service.retrieve_chunks(
                        question=body.question,
                        dataset_ids=dataset_ids,
                        page=1,
                        page_size=30,
                        similarity_threshold=0.2,
                        top_k=30,
                        keyword=False,
                        highlight=False,
                    )
                    chunks = retrieval.get("chunks") if isinstance(retrieval, dict) else None
                    sources: list[dict] = []
                    name_cache: dict[tuple[str, str], str] = {}
                    doc_dataset_cache: dict[str, str] = {}
                    if isinstance(chunks, list):
                        for ch in chunks:
                            if not isinstance(ch, dict):
                                continue
                            doc_id = (
                                ch.get("document_id")
                                or ch.get("docId")
                                or ch.get("documentId")
                                or ch.get("doc_id")
                                or ch.get("id")
                            )
                            dataset_ref = (
                                ch.get("dataset_id")
                                or ch.get("dataset")
                                or ch.get("kb_id")
                                or ch.get("kb")
                                or ch.get("kb_name")
                                or ch.get("dataset_name")
                            )
                            filename = (
                                ch.get("filename")
                                or ch.get("doc_name")
                                or ch.get("document_name")
                                or ch.get("title")
                                or ch.get("name")
                            )
                            chunk_text = (
                                ch.get("content")
                                or ch.get("chunk")
                                or ch.get("text")
                                or ch.get("snippet")
                                or ch.get("content_with_weight")
                            )
                            if not isinstance(doc_id, str) or not doc_id:
                                continue
                            dataset_ref = dataset_ref if isinstance(dataset_ref, str) else ""
                            filename = filename if isinstance(filename, str) else ""
                            if not isinstance(chunk_text, str):
                                chunk_text = ""
                            chunk_text = chunk_text.strip()
                            if len(chunk_text) > 2000:
                                chunk_text = chunk_text[:2000] + "…"

                            def _looks_like_placeholder(name: str) -> bool:
                                if not name:
                                    return True
                                n = name.strip()
                                if not n:
                                    return True
                                if n == doc_id:
                                    return True
                                if n.startswith("document_") and doc_id in n:
                                    return True
                                return False

                            resolved_name = ""
                            resolved_dataset = ""

                            if doc_id in doc_dataset_cache:
                                resolved_dataset = doc_dataset_cache[doc_id]

                            # Prefer dataset from chunk; otherwise try all accessible datasets (best-effort).
                            candidates = []
                            if dataset_ref:
                                try:
                                    ds_name = ragflow_service.resolve_dataset_name(dataset_ref)
                                except Exception:
                                    ds_name = None
                                candidates = [ds_name or dataset_ref]
                            else:
                                candidates = dataset_candidates[:6]

                            # Resolve dataset + name if filename is missing or looks like placeholder.
                            if _looks_like_placeholder(filename) or not resolved_dataset:
                                for dataset_name in candidates:
                                    if not dataset_name:
                                        continue
                                    cache_key = (dataset_name, doc_id)
                                    if cache_key in name_cache:
                                        resolved_name = name_cache[cache_key]
                                        resolved_dataset = dataset_name
                                        break

                                    # Prefer local DB mapping (original uploaded filename) when available.
                                    try:
                                        kb_store = getattr(deps, "kb_store", None)
                                    except Exception:
                                        kb_store = None
                                    if kb_store is not None:
                                        try:
                                            kb_info = resolve_kb_ref(deps, dataset_name)
                                            local_doc = kb_store.get_document_by_ragflow_id(
                                                doc_id,
                                                kb_id=(kb_info.name or kb_info.ref),
                                                kb_refs=list(kb_info.variants),
                                            )
                                        except Exception:
                                            local_doc = None
                                            kb_info = None

                                        local_name = ""
                                        if local_doc is not None:
                                            try:
                                                local_name = str(getattr(local_doc, "filename", "") or "").strip()
                                            except Exception:
                                                local_name = ""

                                        if local_name:
                                            resolved_name = local_name
                                            resolved_dataset = (kb_info.name if kb_info is not None else None) or dataset_name
                                            name_cache[cache_key] = local_name
                                            break

                                    try:
                                        detail = ragflow_service.get_document_detail(doc_id, dataset_name=dataset_name)
                                    except Exception:
                                        detail = None
                                    if isinstance(detail, dict):
                                        n = str(detail.get("name") or "").strip()
                                        if n:
                                            resolved_name = n
                                            resolved_dataset = dataset_name
                                            name_cache[cache_key] = n
                                            break

                            if resolved_dataset:
                                doc_dataset_cache[doc_id] = resolved_dataset

                            final_dataset = resolved_dataset or (candidates[0] if candidates else dataset_ref)
                            final_name = resolved_name or ("" if _looks_like_placeholder(filename) else filename) or doc_id

                            sources.append(
                                {
                                    "doc_id": doc_id,
                                    "dataset": final_dataset,
                                    "filename": final_name,
                                    "chunk": chunk_text,
                                }
                            )
                    return sources
                except Exception as e:
                    logger.warning("[CHAT] Failed to build sources: %s", e)
                    return []

            try:
                sources_task = asyncio.create_task(asyncio.to_thread(_build_sources_sync))
            except Exception:
                sources_task = None

            async for chunk in deps.ragflow_chat_service.chat(
                chat_id=chat_id,
                question=body.question,
                stream=body.stream,
                session_id=body.session_id,
                user_id=user.user_id
            ):
                # SSE格式
                try:
                    if isinstance(chunk, dict):
                        data = chunk.get("data")
                        if isinstance(data, dict):
                            if not effective_session_id:
                                sid = data.get("session_id") or data.get("sessionId") or data.get("session")
                                if sid:
                                    effective_session_id = str(sid).strip() or None
                            ans = data.get("answer")
                            if isinstance(ans, str) and ans:
                                assistant_text_for_hash = ans
                except Exception:
                    pass

                # If sources are ready, send them as a dedicated SSE event (do not block the answer stream).
                try:
                    if sources_task and (not sources_sent) and sources_task.done():
                        sources_sent = True
                        built_sources = sources_task.result() or []
                        if built_sources:
                            yield f"data: {json.dumps({'code': 0, 'data': {'sources': built_sources}}, ensure_ascii=False)}\n\n"
                except Exception as e:
                    sources_sent = True
                    logger.warning("[CHAT] Failed to send sources: %s", e)

                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # Persist assistant sources in sqlite so chat history survives backup/restore.
            try:
                if sources_task and (not sources_sent) and sources_task.done():
                    sources_sent = True
                    built_sources = sources_task.result() or []

                if built_sources and effective_session_id and assistant_text_for_hash:
                    src_store = getattr(deps, "chat_message_sources_store", None)
                    if src_store:
                        src_store.upsert_sources(
                            chat_id=chat_id,
                            session_id=effective_session_id,
                            assistant_text=assistant_text_for_hash,
                            sources=built_sources,
                        )
                        logger.info(
                            "[CHAT] Persisted sources: chat_id=%s session_id=%s hash=%s count=%s",
                            chat_id,
                            effective_session_id,
                            content_hash_hex(assistant_text_for_hash),
                            len(built_sources),
                        )
            except Exception:
                logger.exception("[CHAT] Failed to persist sources")
        except Exception as e:
            logger.error(f"[CHAT] Error during chat: {e}", exc_info=True)
            error_chunk = {"code": -1, "message": str(e)}
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
        finally:
            if sources_task and not sources_task.done():
                try:
                    sources_task.cancel()
                except Exception:
                    pass

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

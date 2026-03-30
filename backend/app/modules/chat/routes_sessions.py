from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.services.chat_message_sources_store import content_hash_hex

from .shared import DeleteSessionsRequest, RenameSessionRequest, assert_chat_access


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chats/{chat_id}/sessions")
def create_session(
    chat_id: str,
    ctx: AuthContextDep,
    name: str = "新会话",
    user_id: Optional[str] = None,
):
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        assert_chat_access(snapshot, chat_id=chat_id)

    session = deps.ragflow_chat_service.create_session(
        chat_id=chat_id,
        name=name,
        user_id=user.user_id,
    )

    if not session:
        raise HTTPException(status_code=500, detail="create_session_failed")

    return session


@router.get("/chats/{chat_id}/sessions")
def list_sessions(
    chat_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        assert_chat_access(snapshot, chat_id=chat_id)

    sessions = deps.ragflow_chat_service.list_sessions(
        chat_id=chat_id,
        user_id=user.user_id,
    )

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

    return {"sessions": sessions, "count": len(sessions)}


@router.put("/chats/{chat_id}/sessions/{session_id}")
def rename_session(
    chat_id: str,
    session_id: str,
    ctx: AuthContextDep,
    body: RenameSessionRequest = Body(...),
):
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        assert_chat_access(snapshot, chat_id=chat_id)

    new_name = str((body.name if body else "") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="name_required")
    if len(new_name) > 120:
        raise HTTPException(status_code=400, detail="name_too_long")

    if not snapshot.is_admin:
        owns_session = deps.chat_session_store.check_ownership(session_id=session_id, chat_id=chat_id, user_id=user.user_id)
        if not owns_session:
            raise HTTPException(status_code=403, detail=f"forbidden_rename_session:{session_id}")

    ok = deps.chat_session_store.set_session_name(
        session_id=session_id,
        chat_id=chat_id,
        user_id=user.user_id,
        name=new_name,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="rename_failed")

    return {"id": session_id, "name": new_name}


@router.delete("/chats/{chat_id}/sessions")
def delete_sessions(
    chat_id: str,
    ctx: AuthContextDep,
    body: DeleteSessionsRequest = None,
):
    session_ids = body.ids if body else None

    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        assert_chat_access(snapshot, chat_id=chat_id)

    if not snapshot.is_admin and session_ids:
        for session_id in session_ids:
            owns_session = deps.chat_session_store.check_ownership(
                session_id=session_id,
                chat_id=chat_id,
                user_id=user.user_id,
            )
            if not owns_session:
                raise HTTPException(status_code=403, detail=f"forbidden_delete_session:{session_id}")

    success = deps.ragflow_chat_service.delete_sessions(
        chat_id=chat_id,
        session_ids=session_ids,
        user_id=user.user_id,
    )

    if not success:
        raise HTTPException(status_code=500, detail="delete_sessions_failed")

    return {"message": "sessions_deleted"}

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.services.chat_message_sources_store import content_hash_hex

from .shared import CreateSessionRequest, DeleteSessionsRequest, RenameSessionRequest, assert_chat_access


router = APIRouter()
logger = logging.getLogger(__name__)


def _normalize_session_messages(session: dict) -> dict:
    messages = session.get("messages")
    if not isinstance(messages, list):
        return session

    normalized_messages = []
    changed = False
    for message in messages:
        if not isinstance(message, dict):
            normalized_messages.append(message)
            continue

        normalized_message = dict(message)
        if "content" not in normalized_message and isinstance(normalized_message.get("answer"), str):
            normalized_message["content"] = normalized_message["answer"]
            changed = True
        if "answer" in normalized_message and "content" in normalized_message:
            normalized_message.pop("answer", None)
            changed = True
        normalized_messages.append(normalized_message)

    if not changed:
        return session

    normalized_session = dict(session)
    normalized_session["messages"] = normalized_messages
    return normalized_session


@router.post("/chats/{chat_id}/sessions")
def create_session(
    chat_id: str,
    ctx: AuthContextDep,
    body: CreateSessionRequest = Body(...),
):
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        assert_chat_access(snapshot, chat_id=chat_id)

    name = str((body.name if body else "") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name_required")

    session = deps.ragflow_chat_service.create_session(
        chat_id=chat_id,
        name=name,
        user_id=user.user_id,
    )

    if not session:
        raise HTTPException(status_code=500, detail="create_session_failed")

    return _normalize_session_messages(session) if isinstance(session, dict) else session


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

    upstream_sessions = deps.ragflow_chat_service.list_sessions(
        chat_id=chat_id,
        user_id=user.user_id,
    )
    sessions = [_normalize_session_messages(s) for s in (upstream_sessions or []) if isinstance(s, dict)]

    try:
        local_sessions = deps.chat_session_store.get_user_sessions(chat_id=chat_id, user_id=user.user_id)
        session_map = {str(s.get("id") or ""): s for s in sessions}
        missing_local_sessions = []
        for local_session in local_sessions or []:
            if not isinstance(local_session, dict):
                continue
            normalized_local_session = _normalize_session_messages(local_session)
            session_id = str(normalized_local_session.get("id") or "").strip()
            if not session_id:
                continue
            local_name = str(normalized_local_session.get("name") or "").strip()
            existing = session_map.get(session_id)
            if existing:
                if local_name:
                    existing["name"] = local_name
                continue
            missing_local_sessions.append(normalized_local_session)
        if missing_local_sessions:
            sessions = missing_local_sessions + sessions
    except Exception:
        logger.exception("Failed to overlay session names from local store")

    try:
        src_store = getattr(deps, "chat_message_sources_store", None)
        if src_store and isinstance(sessions, list):
            for session in sessions:
                if not isinstance(session, dict):
                    continue
                session_id = str(session.get("id") or "")
                messages = session.get("messages")
                if not session_id or not isinstance(messages, list):
                    continue

                hashes: list[str] = []
                idx_to_hash: dict[int, str] = {}
                for index, message in enumerate(messages):
                    if not isinstance(message, dict):
                        continue
                    if str(message.get("role") or "").lower() != "assistant":
                        continue
                    existing = message.get("sources")
                    if isinstance(existing, list) and len(existing) > 0:
                        continue

                    content = str(message.get("content") or "").strip()
                    if not content:
                        continue
                    content_hash = content_hash_hex(content)
                    hashes.append(content_hash)
                    idx_to_hash[index] = content_hash

                if not hashes:
                    continue

                sources_map = src_store.get_sources_map(chat_id=chat_id, session_id=session_id, content_hashes=hashes)
                if not sources_map:
                    continue
                for index, content_hash in idx_to_hash.items():
                    sources = sources_map.get(content_hash)
                    if isinstance(sources, list) and len(sources) > 0:
                        try:
                            messages[index]["sources"] = sources
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

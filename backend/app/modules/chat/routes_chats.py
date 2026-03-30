from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, ValidationError

from backend.app.core.authz import AuthContextDep
from backend.app.core.pydantic_compat import model_dump, model_validate
from backend.app.core.permission_resolver import ResourceScope, normalize_accessible_chat_ids

from .shared import assert_chat_access


router = APIRouter()
logger = logging.getLogger(__name__)


class ChatCreateBody(BaseModel):
    name: Any = None

    class Config:
        extra = "allow"


class ChatUpdateBody(BaseModel):
    name: Any = None

    class Config:
        extra = "allow"


def _coerce_chat_list(value: object, *, source: str) -> list[dict]:
    if not isinstance(value, list):
        logger.warning("ragflow_chat_service.%s returned non-list: %s", source, type(value).__name__)
        return []
    out = [chat for chat in value if isinstance(chat, dict)]
    filtered = len(value) - len(out)
    if filtered > 0:
        logger.warning("ragflow_chat_service.%s dropped non-dict chat items: %d", source, filtered)
    return out


@router.post("/chats/{chat_id}/clear-parsed-files")
def clear_parsed_files(
    chat_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    try:
        updated = deps.ragflow_chat_service.clear_chat_parsed_files(chat_id)
    except ValueError as e:
        code = str(e) or "chat_clear_parsed_failed"
        if code == "chat_not_found":
            raise HTTPException(status_code=404, detail="chat_not_found")
        raise HTTPException(status_code=422, detail=code)
    except Exception as e:
        logger.error("[chats.clear_parsed] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=str(e) or "chat_clear_parsed_failed")

    if not updated:
        raise HTTPException(status_code=500, detail="chat_clear_parsed_failed")

    return {"chat": updated}


@router.post("/chats")
def create_chat(
    ctx: AuthContextDep,
    body: object = Body(...),
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid_body")

    try:
        parsed = model_validate(ChatCreateBody, body)
    except ValidationError:
        raise HTTPException(status_code=400, detail="invalid_body")

    raw = model_dump(parsed, include_none=True)
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="missing_name")

    payload = dict(raw)
    payload["name"] = name.strip()
    payload.pop("id", None)
    payload.pop("chat_id", None)

    try:
        created = deps.ragflow_chat_service.create_chat(payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e) or "chat_create_failed")
    except Exception as e:
        logger.error("[chats.create] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=str(e) or "chat_create_failed")

    if not created:
        raise HTTPException(status_code=500, detail="chat_create_failed")

    return {"chat": created}


@router.put("/chats/{chat_id}")
def update_chat(
    chat_id: str,
    ctx: AuthContextDep,
    updates: object = Body(...),
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="invalid_updates")

    try:
        parsed = model_validate(ChatUpdateBody, updates)
    except ValidationError:
        raise HTTPException(status_code=400, detail="invalid_updates")

    updates = dict(model_dump(parsed, include_none=True))
    updates.pop("id", None)
    updates.pop("chat_id", None)

    try:
        updated = deps.ragflow_chat_service.update_chat(chat_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e) or "chat_update_failed")
    except Exception as e:
        logger.error("[chats.update] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=str(e) or "chat_update_failed")

    if not updated:
        raise HTTPException(status_code=500, detail="chat_update_failed")

    return {"chat": updated}


@router.delete("/chats/{chat_id}")
def delete_chat(
    chat_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    try:
        deps.ragflow_chat_service.delete_chat(chat_id)
    except ValueError as e:
        code = str(e) or "chat_delete_failed"
        if code == "chat_not_found":
            raise HTTPException(status_code=404, detail="chat_not_found")
        raise HTTPException(status_code=422, detail=code)
    except Exception as e:
        logger.error("[chats.delete] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=str(e) or "chat_delete_failed")

    return {"ok": True}


@router.get("/chats")
def list_chats(
    ctx: AuthContextDep,
    page: int = 1,
    page_size: int = 30,
    orderby: str = "create_time",
    desc: bool = True,
    name: Optional[str] = None,
    chat_id: Optional[str] = None,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    all_chats = deps.ragflow_chat_service.list_chats(
        page=page,
        page_size=page_size,
        orderby=orderby,
        desc=desc,
        name=name,
        chat_id=chat_id,
    )
    all_chats = _coerce_chat_list(all_chats, source="list_chats")

    if not snapshot.is_admin:
        if snapshot.chat_scope == ResourceScope.NONE:
            return {"chats": [], "count": 0}
        allowed_ids = normalize_accessible_chat_ids(snapshot.chat_ids)
        all_chats = [chat for chat in all_chats if isinstance(chat, dict) and chat.get("id") in allowed_ids]

    return {"chats": all_chats, "count": len(all_chats)}


@router.get("/chats/my")
def get_my_chats(
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    all_chats = deps.ragflow_chat_service.list_chats(page_size=1000)
    all_chats = _coerce_chat_list(all_chats, source="list_chats")

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

    return {"chats": filtered_chats, "count": len(filtered_chats)}


@router.get("/chats/{chat_id}")
def get_chat(
    chat_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    if not snapshot.is_admin:
        assert_chat_access(snapshot, chat_id=chat_id)

    chat = deps.ragflow_chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="chat_not_found")

    return chat

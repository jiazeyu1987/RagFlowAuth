from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError

from backend.app.core.authz import AuthContextDep
from backend.app.core.pydantic_compat import model_dump, model_validate
from backend.app.core.permission_resolver import ResourceScope, normalize_accessible_chat_ids
from backend.models.auth import ResultEnvelope
from backend.models.chat import ChatEnvelope, ChatListEnvelope

from .shared import assert_chat_access


router = APIRouter()
logger = logging.getLogger(__name__)


class ChatCreateBody(BaseModel):
    name: Any = None

    model_config = ConfigDict(extra="allow")


class ChatUpdateBody(BaseModel):
    name: Any = None

    model_config = ConfigDict(extra="allow")


def _wrap_result(message: str, **extra: object) -> dict[str, dict[str, object]]:
    result: dict[str, object] = {"message": message}
    result.update(extra)
    return {"result": result}


def _require_chat_payload(value: object, *, detail: str) -> dict:
    if not isinstance(value, dict):
        raise HTTPException(status_code=502, detail=detail)
    return value


def _require_chat_list(value: object, *, detail: str) -> list[dict]:
    if not isinstance(value, list):
        raise HTTPException(status_code=502, detail=detail)
    for chat in value:
        if not isinstance(chat, dict):
            raise HTTPException(status_code=502, detail=detail)
    return value


def _chat_management_manager(ctx: AuthContextDep):
    manager = getattr(ctx.deps, "chat_management_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="chat_management_manager_unavailable")
    return manager


def _assert_sub_admin_chat_management(ctx: AuthContextDep, *, chat_id: str | None = None, payload: dict | None = None) -> None:
    role = str(getattr(ctx.user, "role", "") or "").strip().lower()
    if ctx.snapshot.is_admin:
        return
    if role != "sub_admin":
        raise HTTPException(status_code=403, detail="admin_required")
    manager = _chat_management_manager(ctx)
    try:
        if chat_id is not None:
            manager.assert_chat_manageable(user=ctx.user, chat_id=chat_id)
        if payload is not None:
            manager.validate_chat_payload(user=ctx.user, payload=payload)
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc


@router.post("/chats/{chat_id}/clear-parsed-files", response_model=ChatEnvelope)
def clear_parsed_files(
    chat_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        _assert_sub_admin_chat_management(ctx, chat_id=chat_id)

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

    updated = _require_chat_payload(updated, detail="chat_clear_parsed_invalid_payload")

    return {"chat": updated}


@router.post("/chats", response_model=ChatEnvelope)
def create_chat(
    ctx: AuthContextDep,
    body: object = Body(...),
):
    deps = ctx.deps
    snapshot = ctx.snapshot

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

    if not snapshot.is_admin:
        _assert_sub_admin_chat_management(ctx, payload=payload)

    try:
        created = deps.ragflow_chat_service.create_chat(payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e) or "chat_create_failed")
    except Exception as e:
        logger.error("[chats.create] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=str(e) or "chat_create_failed")

    created = _require_chat_payload(created, detail="chat_create_invalid_payload")

    if not snapshot.is_admin:
        manager = _chat_management_manager(ctx)
        try:
            manager.record_created_chat(user=ctx.user, chat=created)
        except Exception as exc:
            raise HTTPException(status_code=int(getattr(exc, "status_code", 500) or 500), detail=str(exc)) from exc

    return {"chat": created}


@router.put("/chats/{chat_id}", response_model=ChatEnvelope)
def update_chat(
    chat_id: str,
    ctx: AuthContextDep,
    updates: object = Body(...),
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="invalid_updates")

    try:
        parsed = model_validate(ChatUpdateBody, updates)
    except ValidationError:
        raise HTTPException(status_code=400, detail="invalid_updates")

    updates = dict(model_dump(parsed, include_none=True))
    updates.pop("id", None)
    updates.pop("chat_id", None)

    if not snapshot.is_admin:
        _assert_sub_admin_chat_management(ctx, chat_id=chat_id, payload=updates)

    try:
        updated = deps.ragflow_chat_service.update_chat(chat_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e) or "chat_update_failed")
    except Exception as e:
        logger.error("[chats.update] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=str(e) or "chat_update_failed")

    updated = _require_chat_payload(updated, detail="chat_update_invalid_payload")

    return {"chat": updated}


@router.delete("/chats/{chat_id}", response_model=ResultEnvelope)
def delete_chat(
    chat_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        _assert_sub_admin_chat_management(ctx, chat_id=chat_id)

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

    manager = getattr(ctx.deps, "chat_management_manager", None)
    if manager is not None:
        manager.cleanup_deleted_chat(chat_id)
    return _wrap_result("chat_deleted")


@router.get("/chats", response_model=ChatListEnvelope)
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
    all_chats = _require_chat_list(all_chats, detail="chat_list_invalid_payload")

    role = str(getattr(ctx.user, "role", "") or "").strip().lower()
    if snapshot.is_admin:
        pass
    elif role == "sub_admin":
        manager = _chat_management_manager(ctx)
        try:
            allowed_ids = manager.list_manageable_chat_ids(ctx.user)
        except Exception as exc:
            raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc
        all_chats = [chat for chat in all_chats if isinstance(chat, dict) and str(chat.get("id") or "").strip() in allowed_ids]
    else:
        if snapshot.chat_scope == ResourceScope.NONE:
            return {"chats": [], "count": 0}
        allowed_ids = normalize_accessible_chat_ids(snapshot.chat_ids)
        all_chats = [chat for chat in all_chats if isinstance(chat, dict) and chat.get("id") in allowed_ids]

    return {"chats": all_chats, "count": len(all_chats)}


@router.get("/chats/my", response_model=ChatListEnvelope)
def get_my_chats(
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    all_chats = deps.ragflow_chat_service.list_chats(page_size=1000)
    all_chats = _require_chat_list(all_chats, detail="chat_list_invalid_payload")

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


@router.get("/chats/{chat_id}", response_model=ChatEnvelope)
def get_chat(
    chat_id: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    role = str(getattr(ctx.user, "role", "") or "").strip().lower()
    if not snapshot.is_admin:
        if role == "sub_admin":
            _assert_sub_admin_chat_management(ctx, chat_id=chat_id)
        else:
            assert_chat_access(snapshot, chat_id=chat_id)

    chat = deps.ragflow_chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="chat_not_found")
    chat = _require_chat_payload(chat, detail="chat_invalid_payload")

    return {"chat": chat}

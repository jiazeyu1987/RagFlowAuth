from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel

from backend.app.core.permission_resolver import ResourceScope, normalize_accessible_chat_ids


def assert_chat_access(snapshot, chat_id: Optional[str] = None) -> set[str]:
    if snapshot.chat_scope == ResourceScope.ALL:
        return set()
    if snapshot.chat_scope == ResourceScope.NONE:
        raise HTTPException(status_code=403, detail="forbidden_chat_access")

    allowed_raw_ids = normalize_accessible_chat_ids(snapshot.chat_ids)
    if chat_id is not None and chat_id not in allowed_raw_ids:
        raise HTTPException(status_code=403, detail="forbidden_chat_access")
    return allowed_raw_ids


class ChatCompletionRequest(BaseModel):
    question: str
    stream: bool = True
    session_id: Optional[str] = None


class DeleteSessionsRequest(BaseModel):
    ids: Optional[list[str]] = None


class RenameSessionRequest(BaseModel):
    name: str


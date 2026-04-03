from __future__ import annotations

from pydantic import BaseModel


class InboxMarkReadResponse(BaseModel):
    inbox_id: str
    status: str


class InboxMarkAllReadResponse(BaseModel):
    updated: int
    unread_count: int

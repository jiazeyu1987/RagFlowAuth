from __future__ import annotations

from pydantic import BaseModel


class InboxMarkReadResult(BaseModel):
    message: str
    inbox_id: str
    status: str


class InboxMarkAllReadResult(BaseModel):
    message: str
    updated: int
    unread_count: int


class InboxMarkReadResponse(BaseModel):
    result: InboxMarkReadResult


class InboxMarkAllReadResponse(BaseModel):
    result: InboxMarkAllReadResult

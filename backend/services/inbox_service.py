from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .inbox_store import UserInboxStore


@dataclass
class UserInboxError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class UserInboxService:
    def __init__(self, store: UserInboxStore):
        self._store = store

    def notify_users(
        self,
        *,
        recipients: list[dict[str, Any]],
        title: str,
        body: str,
        event_type: str,
        link_path: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> list[dict]:
        items: list[dict] = []
        for recipient in recipients or []:
            user_id = str((recipient or {}).get("user_id") or "").strip()
            if not user_id:
                continue
            items.append(
                self._store.create_item(
                    recipient_user_id=user_id,
                    recipient_username=(str(recipient.get("username")) if recipient.get("username") else None),
                    title=str(title or "").strip(),
                    body=str(body or "").strip(),
                    link_path=(str(link_path) if link_path else None),
                    event_type=str(event_type or "").strip() or "inbox_event",
                    payload=payload or {},
                )
            )
        return items

    def list_items(self, *, recipient_user_id: str, unread_only: bool = False, limit: int = 100) -> dict:
        items = self._store.list_items(
            recipient_user_id=recipient_user_id,
            unread_only=bool(unread_only),
            limit=limit,
        )
        unread_count = self._store.count_unread(recipient_user_id=recipient_user_id)
        return {
            "items": items,
            "count": len(items),
            "unread_count": unread_count,
        }

    def mark_read(self, *, inbox_id: str, recipient_user_id: str) -> dict:
        item = self._store.mark_read(inbox_id=inbox_id, recipient_user_id=recipient_user_id)
        if not item:
            raise UserInboxError("inbox_notification_not_found", status_code=404)
        return item

    def mark_all_read(self, *, recipient_user_id: str) -> dict:
        updated = self._store.mark_all_read(recipient_user_id=recipient_user_id)
        return {
            "updated": updated,
            "unread_count": self._store.count_unread(recipient_user_id=recipient_user_id),
        }

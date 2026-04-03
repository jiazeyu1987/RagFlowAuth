from __future__ import annotations

import json
import time
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


def _to_json_text(value) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _from_json_text(value: str | None):
    if not value:
        return {}
    return json.loads(value)


class UserInboxStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    def create_item(
        self,
        *,
        recipient_user_id: str,
        recipient_username: str | None,
        title: str,
        body: str,
        link_path: str | None,
        event_type: str,
        payload: dict,
    ) -> dict:
        inbox_id = str(uuid4())
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO user_inbox_notifications (
                    inbox_id, recipient_user_id, recipient_username, title, body, link_path,
                    event_type, payload_json, status, created_at_ms, read_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unread', ?, NULL)
                """,
                (
                    inbox_id,
                    recipient_user_id,
                    recipient_username,
                    title,
                    body,
                    link_path,
                    event_type,
                    _to_json_text(payload),
                    now_ms,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        item = self.get_item(inbox_id)
        if not item:
            raise RuntimeError("user_inbox_create_failed")
        return item

    def get_item(self, inbox_id: str) -> dict | None:
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT
                    inbox_id, recipient_user_id, recipient_username, title, body, link_path,
                    event_type, payload_json, status, created_at_ms, read_at_ms
                FROM user_inbox_notifications
                WHERE inbox_id = ?
                """,
                (inbox_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "inbox_id": str(row["inbox_id"]),
                "recipient_user_id": str(row["recipient_user_id"]),
                "recipient_username": (str(row["recipient_username"]) if row["recipient_username"] else None),
                "title": str(row["title"]),
                "body": str(row["body"]),
                "link_path": (str(row["link_path"]) if row["link_path"] else None),
                "event_type": str(row["event_type"]),
                "payload": _from_json_text(row["payload_json"]),
                "status": str(row["status"]),
                "created_at_ms": int(row["created_at_ms"] or 0),
                "read_at_ms": (int(row["read_at_ms"]) if row["read_at_ms"] is not None else None),
            }
        finally:
            conn.close()

    def list_items(self, *, recipient_user_id: str, unread_only: bool = False, limit: int = 100) -> list[dict]:
        lim = max(1, min(500, int(limit)))
        conn = self._conn()
        try:
            if unread_only:
                rows = conn.execute(
                    """
                    SELECT inbox_id
                    FROM user_inbox_notifications
                    WHERE recipient_user_id = ? AND status = 'unread'
                    ORDER BY created_at_ms DESC
                    LIMIT ?
                    """,
                    (recipient_user_id, lim),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT inbox_id
                    FROM user_inbox_notifications
                    WHERE recipient_user_id = ?
                    ORDER BY created_at_ms DESC
                    LIMIT ?
                    """,
                    (recipient_user_id, lim),
                ).fetchall()
            return [self.get_item(str(row["inbox_id"])) for row in rows if row]
        finally:
            conn.close()

    def count_unread(self, *, recipient_user_id: str) -> int:
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT COUNT(1) AS c
                FROM user_inbox_notifications
                WHERE recipient_user_id = ? AND status = 'unread'
                """,
                (recipient_user_id,),
            ).fetchone()
            return int(row["c"] or 0) if row else 0
        finally:
            conn.close()

    def mark_read(self, *, inbox_id: str, recipient_user_id: str) -> dict | None:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE user_inbox_notifications
                SET status = 'read', read_at_ms = COALESCE(read_at_ms, ?)
                WHERE inbox_id = ? AND recipient_user_id = ?
                """,
                (now_ms, inbox_id, recipient_user_id),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_item(inbox_id)

    def mark_all_read(self, *, recipient_user_id: str) -> int:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                UPDATE user_inbox_notifications
                SET status = 'read', read_at_ms = COALESCE(read_at_ms, ?)
                WHERE recipient_user_id = ? AND status = 'unread'
                """,
                (now_ms, recipient_user_id),
            )
            conn.commit()
            return int(cur.rowcount or 0)
        finally:
            conn.close()

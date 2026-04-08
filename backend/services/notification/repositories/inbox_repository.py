from __future__ import annotations

import time
from typing import Any

from .common import ConnectFactory, from_json_text


class NotificationInboxRepository:
    def __init__(self, connect: ConnectFactory):
        self._connect = connect

    def list_inbox(
        self,
        *,
        recipient_user_id: str,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> tuple[int, int, list[dict[str, Any]]]:
        recipient_user_id = str(recipient_user_id or "").strip()
        if not recipient_user_id:
            raise ValueError("recipient_user_id_required")
        lim = max(1, min(500, int(limit)))
        off = max(0, int(offset))
        base_where = """
            FROM notification_jobs j
            JOIN notification_channels c ON c.channel_id = j.channel_id
            WHERE c.channel_type = 'in_app'
              AND j.status = 'sent'
              AND j.recipient_user_id = ?
        """
        unread_cond = " AND j.read_at_ms IS NULL"

        conn = self._connect()
        try:
            total_row = conn.execute(f"SELECT COUNT(*) {base_where}", (recipient_user_id,)).fetchone()
            unread_row = conn.execute(f"SELECT COUNT(*) {base_where}{unread_cond}", (recipient_user_id,)).fetchone()
            total = int(total_row[0]) if total_row else 0
            unread_count = int(unread_row[0]) if unread_row else 0
            rows = conn.execute(
                f"""
                SELECT
                    j.job_id,
                    j.channel_id,
                    c.name AS channel_name,
                    j.event_type,
                    j.payload_json,
                    j.recipient_user_id,
                    j.recipient_username,
                    j.recipient_address,
                    j.status,
                    j.created_at_ms,
                    j.sent_at_ms,
                    j.read_at_ms
                {base_where}
                {"AND j.read_at_ms IS NULL" if unread_only else ""}
                ORDER BY j.created_at_ms DESC, j.job_id DESC
                LIMIT ? OFFSET ?
                """,
                (recipient_user_id, lim, off),
            ).fetchall()
            items = [
                {
                    "job_id": int(row["job_id"]),
                    "channel_id": str(row["channel_id"]),
                    "channel_name": str(row["channel_name"] or ""),
                    "event_type": str(row["event_type"]),
                    "payload": from_json_text(row["payload_json"]) or {},
                    "recipient_user_id": row["recipient_user_id"],
                    "recipient_username": row["recipient_username"],
                    "recipient_address": row["recipient_address"],
                    "status": str(row["status"]),
                    "created_at_ms": int(row["created_at_ms"] or 0),
                    "sent_at_ms": (int(row["sent_at_ms"]) if row["sent_at_ms"] is not None else None),
                    "read_at_ms": (int(row["read_at_ms"]) if row["read_at_ms"] is not None else None),
                }
                for row in rows
            ]
            return total, unread_count, items
        finally:
            conn.close()

    def set_inbox_read_state(
        self,
        *,
        job_id: int,
        recipient_user_id: str,
        read: bool,
    ) -> int | None:
        recipient_user_id = str(recipient_user_id or "").strip()
        if not recipient_user_id:
            raise ValueError("recipient_user_id_required")
        now_ms = int(time.time() * 1000)
        conn = self._connect()
        try:
            existing = conn.execute(
                """
                SELECT j.job_id
                FROM notification_jobs j
                JOIN notification_channels c ON c.channel_id = j.channel_id
                WHERE j.job_id = ?
                  AND c.channel_type = 'in_app'
                  AND j.status = 'sent'
                  AND j.recipient_user_id = ?
                """,
                (int(job_id), recipient_user_id),
            ).fetchone()
            if not existing:
                return None
            conn.execute(
                """
                UPDATE notification_jobs
                SET read_at_ms = ?
                WHERE job_id = ?
                """,
                (now_ms if bool(read) else None, int(job_id)),
            )
            conn.commit()
            return int(existing["job_id"])
        finally:
            conn.close()

    def mark_all_inbox_read(self, *, recipient_user_id: str) -> int:
        recipient_user_id = str(recipient_user_id or "").strip()
        if not recipient_user_id:
            raise ValueError("recipient_user_id_required")
        now_ms = int(time.time() * 1000)
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                UPDATE notification_jobs
                SET read_at_ms = ?
                WHERE job_id IN (
                    SELECT j.job_id
                    FROM notification_jobs j
                    JOIN notification_channels c ON c.channel_id = j.channel_id
                    WHERE c.channel_type = 'in_app'
                      AND j.status = 'sent'
                      AND j.recipient_user_id = ?
                      AND j.read_at_ms IS NULL
                )
                """,
                (now_ms, recipient_user_id),
            )
            changed = int(cur.rowcount or 0)
            conn.commit()
            return changed
        finally:
            conn.close()

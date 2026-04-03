from __future__ import annotations

import json
import time
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


def _to_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _from_json_text(value: str | None) -> Any:
    if not value:
        return None
    return json.loads(value)


class NotificationStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    def upsert_channel(
        self,
        *,
        channel_id: str,
        channel_type: str,
        name: str,
        enabled: bool,
        config: dict[str, Any] | None,
    ) -> dict[str, Any]:
        channel_id = str(channel_id or "").strip()
        channel_type = str(channel_type or "").strip().lower()
        name = str(name or "").strip()
        if channel_type not in {"email", "dingtalk", "in_app"}:
            raise ValueError("invalid_channel_type")
        if not channel_id:
            raise ValueError("channel_id_required")
        if not name:
            raise ValueError("channel_name_required")
        now_ms = int(time.time() * 1000)
        config_json = _to_json_text(config or {})
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO notification_channels (
                    channel_id, channel_type, name, enabled, config_json, created_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    channel_type=excluded.channel_type,
                    name=excluded.name,
                    enabled=excluded.enabled,
                    config_json=excluded.config_json,
                    updated_at_ms=excluded.updated_at_ms
                """,
                (channel_id, channel_type, name, 1 if enabled else 0, config_json, now_ms, now_ms),
            )
            conn.commit()
        finally:
            conn.close()
        item = self.get_channel(channel_id)
        if not item:
            raise RuntimeError("notification_channel_upsert_failed")
        return item

    def get_channel(self, channel_id: str) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT channel_id, channel_type, name, enabled, config_json, created_at_ms, updated_at_ms
                FROM notification_channels
                WHERE channel_id = ?
                """,
                (channel_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "channel_id": row["channel_id"],
                "channel_type": row["channel_type"],
                "name": row["name"],
                "enabled": bool(row["enabled"]),
                "config": _from_json_text(row["config_json"]) or {},
                "created_at_ms": int(row["created_at_ms"] or 0),
                "updated_at_ms": int(row["updated_at_ms"] or 0),
            }
        finally:
            conn.close()

    def list_channels(self, *, enabled_only: bool = False) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            if enabled_only:
                rows = conn.execute(
                    """
                    SELECT channel_id
                    FROM notification_channels
                    WHERE enabled = 1
                    ORDER BY updated_at_ms DESC
                    """
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT channel_id
                    FROM notification_channels
                    ORDER BY updated_at_ms DESC
                    """
                ).fetchall()
            out: list[dict[str, Any]] = []
            for row in rows:
                item = self.get_channel(str(row["channel_id"]))
                if item:
                    out.append(item)
            return out
        finally:
            conn.close()

    def create_job(
        self,
        *,
        channel_id: str,
        event_type: str,
        payload: dict[str, Any],
        recipient_user_id: str | None = None,
        recipient_username: str | None = None,
        recipient_address: str | None = None,
        dedupe_key: str | None = None,
        source_job_id: int | None = None,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        payload_json = _to_json_text(payload or {})
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO notification_jobs (
                    channel_id,
                    event_type,
                    payload_json,
                    recipient_user_id,
                    recipient_username,
                    recipient_address,
                    dedupe_key,
                    source_job_id,
                    status,
                    attempts,
                    max_attempts,
                    created_at_ms,
                    read_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', 0, ?, ?, NULL)
                """,
                (
                    channel_id,
                    event_type,
                    payload_json,
                    recipient_user_id,
                    recipient_username,
                    recipient_address,
                    dedupe_key,
                    int(source_job_id) if source_job_id is not None else None,
                    int(max_attempts),
                    now_ms,
                ),
            )
            job_id = int(cur.lastrowid)
            conn.commit()
        finally:
            conn.close()
        item = self.get_job(job_id)
        if not item:
            raise RuntimeError("notification_job_create_failed")
        return item

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT
                    job_id,
                    channel_id,
                    event_type,
                    payload_json,
                    recipient_user_id,
                    recipient_username,
                    recipient_address,
                    dedupe_key,
                    source_job_id,
                    status,
                    attempts,
                    max_attempts,
                    last_error,
                    created_at_ms,
                    sent_at_ms,
                    next_retry_at_ms,
                    read_at_ms
                FROM notification_jobs
                WHERE job_id = ?
                """,
                (int(job_id),),
            ).fetchone()
            if not row:
                return None
            return {
                "job_id": int(row["job_id"]),
                "channel_id": row["channel_id"],
                "event_type": row["event_type"],
                "payload": _from_json_text(row["payload_json"]) or {},
                "recipient_user_id": row["recipient_user_id"],
                "recipient_username": row["recipient_username"],
                "recipient_address": row["recipient_address"],
                "dedupe_key": row["dedupe_key"],
                "source_job_id": (int(row["source_job_id"]) if row["source_job_id"] is not None else None),
                "status": row["status"],
                "attempts": int(row["attempts"] or 0),
                "max_attempts": int(row["max_attempts"] or 0),
                "last_error": row["last_error"],
                "created_at_ms": int(row["created_at_ms"] or 0),
                "sent_at_ms": (int(row["sent_at_ms"]) if row["sent_at_ms"] is not None else None),
                "next_retry_at_ms": (int(row["next_retry_at_ms"]) if row["next_retry_at_ms"] is not None else None),
                "read_at_ms": (int(row["read_at_ms"]) if row["read_at_ms"] is not None else None),
            }
        finally:
            conn.close()

    def list_jobs(self, *, limit: int = 100, status: str | None = None) -> list[dict[str, Any]]:
        lim = max(1, min(500, int(limit)))
        conn = self._conn()
        try:
            if status:
                rows = conn.execute(
                    """
                    SELECT job_id
                    FROM notification_jobs
                    WHERE status = ?
                    ORDER BY created_at_ms DESC
                    LIMIT ?
                    """,
                    (status, lim),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT job_id
                    FROM notification_jobs
                    ORDER BY created_at_ms DESC
                    LIMIT ?
                    """,
                    (lim,),
                ).fetchall()
            out: list[dict[str, Any]] = []
            for row in rows:
                item = self.get_job(int(row["job_id"]))
                if item:
                    out.append(item)
            return out
        finally:
            conn.close()

    def find_duplicate_job(
        self,
        *,
        channel_id: str,
        event_type: str,
        recipient_user_id: str | None,
        dedupe_key: str | None,
    ) -> dict[str, Any] | None:
        if not dedupe_key:
            return None
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT job_id
                FROM notification_jobs
                WHERE channel_id = ?
                  AND event_type = ?
                  AND dedupe_key = ?
                  AND COALESCE(recipient_user_id, '') = COALESCE(?, '')
                ORDER BY job_id DESC
                LIMIT 1
                """,
                (channel_id, event_type, dedupe_key, recipient_user_id),
            ).fetchone()
            if not row:
                return None
            return self.get_job(int(row["job_id"]))
        finally:
            conn.close()

    def reset_job_for_retry(self, *, job_id: int) -> dict[str, Any]:
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE notification_jobs
                SET
                    status = 'queued',
                    attempts = 0,
                    last_error = NULL,
                    sent_at_ms = NULL,
                    next_retry_at_ms = NULL
                WHERE job_id = ?
                """,
                (int(job_id),),
            )
            conn.commit()
        finally:
            conn.close()
        item = self.get_job(job_id)
        if not item:
            raise RuntimeError("notification_job_not_found_after_reset")
        return item

    def clone_job_for_resend(self, *, job_id: int, dedupe_key: str) -> dict[str, Any]:
        source = self.get_job(int(job_id))
        if not source:
            raise RuntimeError("notification_job_not_found_for_resend")
        return self.create_job(
            channel_id=str(source["channel_id"]),
            event_type=str(source["event_type"]),
            payload=source.get("payload") or {},
            recipient_user_id=(str(source["recipient_user_id"]) if source.get("recipient_user_id") else None),
            recipient_username=(str(source["recipient_username"]) if source.get("recipient_username") else None),
            recipient_address=(str(source["recipient_address"]) if source.get("recipient_address") else None),
            dedupe_key=dedupe_key,
            source_job_id=int(source["job_id"]),
            max_attempts=int(source["max_attempts"] or 3),
        )

    def mark_job_sent(self, *, job_id: int) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE notification_jobs
                SET status = 'sent', sent_at_ms = ?, last_error = NULL, next_retry_at_ms = NULL
                WHERE job_id = ?
                """,
                (now_ms, int(job_id)),
            )
            conn.commit()
        finally:
            conn.close()
        item = self.get_job(job_id)
        if not item:
            raise RuntimeError("notification_job_not_found_after_sent")
        return item

    def mark_job_failed(self, *, job_id: int, error: str, retry_interval_seconds: int) -> dict[str, Any]:
        retry_ms = max(1, int(retry_interval_seconds)) * 1000
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE notification_jobs
                SET
                    attempts = attempts + 1,
                    status = CASE
                        WHEN attempts + 1 >= max_attempts THEN 'failed'
                        ELSE 'queued'
                    END,
                    last_error = ?,
                    next_retry_at_ms = CASE
                        WHEN attempts + 1 >= max_attempts THEN NULL
                        ELSE ?
                    END
                WHERE job_id = ?
                """,
                (str(error), now_ms + retry_ms, int(job_id)),
            )
            conn.commit()
        finally:
            conn.close()
        item = self.get_job(job_id)
        if not item:
            raise RuntimeError("notification_job_not_found_after_failed")
        return item

    def list_dispatchable_jobs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        lim = max(1, min(500, int(limit)))
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT job_id
                FROM notification_jobs
                WHERE status = 'queued'
                  AND (next_retry_at_ms IS NULL OR next_retry_at_ms <= ?)
                  AND attempts < max_attempts
                ORDER BY created_at_ms ASC
                LIMIT ?
                """,
                (now_ms, lim),
            ).fetchall()
            out: list[dict[str, Any]] = []
            for row in rows:
                item = self.get_job(int(row["job_id"]))
                if item:
                    out.append(item)
            return out
        finally:
            conn.close()

    def add_delivery_log(self, *, job_id: int, channel_id: str, status: str, error: str | None = None) -> None:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO notification_delivery_logs (job_id, channel_id, status, error, attempted_at_ms)
                VALUES (?, ?, ?, ?, ?)
                """,
                (int(job_id), channel_id, status, error, now_ms),
            )
            conn.commit()
        finally:
            conn.close()

    def list_delivery_logs(self, *, job_id: int, limit: int = 50) -> list[dict[str, Any]]:
        lim = max(1, min(500, int(limit)))
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT id, job_id, channel_id, status, error, attempted_at_ms
                FROM notification_delivery_logs
                WHERE job_id = ?
                ORDER BY attempted_at_ms DESC, id DESC
                LIMIT ?
                """,
                (int(job_id), lim),
            ).fetchall()
            return [
                {
                    "id": int(row["id"]),
                    "job_id": int(row["job_id"]),
                    "channel_id": str(row["channel_id"]),
                    "status": str(row["status"]),
                    "error": row["error"],
                    "attempted_at_ms": int(row["attempted_at_ms"] or 0),
                }
                for row in rows
            ]
        finally:
            conn.close()

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

        base_where = (
            """
            FROM notification_jobs j
            JOIN notification_channels c ON c.channel_id = j.channel_id
            WHERE c.channel_type = 'in_app'
              AND j.status = 'sent'
              AND j.recipient_user_id = ?
            """
        )
        unread_cond = " AND j.read_at_ms IS NULL"

        conn = self._conn()
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
            items: list[dict[str, Any]] = []
            for row in rows:
                items.append(
                    {
                        "job_id": int(row["job_id"]),
                        "channel_id": str(row["channel_id"]),
                        "channel_name": str(row["channel_name"] or ""),
                        "event_type": str(row["event_type"]),
                        "payload": _from_json_text(row["payload_json"]) or {},
                        "recipient_user_id": row["recipient_user_id"],
                        "recipient_username": row["recipient_username"],
                        "recipient_address": row["recipient_address"],
                        "status": str(row["status"]),
                        "created_at_ms": int(row["created_at_ms"] or 0),
                        "sent_at_ms": (int(row["sent_at_ms"]) if row["sent_at_ms"] is not None else None),
                        "read_at_ms": (int(row["read_at_ms"]) if row["read_at_ms"] is not None else None),
                    }
                )
            return total, unread_count, items
        finally:
            conn.close()

    def set_inbox_read_state(
        self,
        *,
        job_id: int,
        recipient_user_id: str,
        read: bool,
    ) -> dict[str, Any] | None:
        recipient_user_id = str(recipient_user_id or "").strip()
        if not recipient_user_id:
            raise ValueError("recipient_user_id_required")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
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
        finally:
            conn.close()

        return self.get_job(int(job_id))

    def mark_all_inbox_read(self, *, recipient_user_id: str) -> int:
        recipient_user_id = str(recipient_user_id or "").strip()
        if not recipient_user_id:
            raise ValueError("recipient_user_id_required")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
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

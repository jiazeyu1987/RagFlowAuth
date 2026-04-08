from __future__ import annotations

import time
from typing import Any

from .common import ConnectFactory, from_json_text, to_json_text


class NotificationJobRepository:
    def __init__(self, connect: ConnectFactory):
        self._connect = connect

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
        conn = self._connect()
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
                    to_json_text(payload or {}),
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
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT
                    j.job_id,
                    j.channel_id,
                    c.channel_type,
                    c.name AS channel_name,
                    j.event_type,
                    j.payload_json,
                    j.recipient_user_id,
                    j.recipient_username,
                    j.recipient_address,
                    j.dedupe_key,
                    j.source_job_id,
                    j.status,
                    j.attempts,
                    j.max_attempts,
                    j.last_error,
                    j.created_at_ms,
                    j.sent_at_ms,
                    j.next_retry_at_ms,
                    j.read_at_ms
                FROM notification_jobs j
                LEFT JOIN notification_channels c ON c.channel_id = j.channel_id
                WHERE j.job_id = ?
                """,
                (int(job_id),),
            ).fetchone()
            if not row:
                return None
            return {
                "job_id": int(row["job_id"]),
                "channel_id": str(row["channel_id"]),
                "channel_type": (str(row["channel_type"]) if row["channel_type"] is not None else None),
                "channel_name": (str(row["channel_name"]) if row["channel_name"] is not None else None),
                "event_type": str(row["event_type"]),
                "payload": from_json_text(row["payload_json"]) or {},
                "recipient_user_id": row["recipient_user_id"],
                "recipient_username": row["recipient_username"],
                "recipient_address": row["recipient_address"],
                "dedupe_key": row["dedupe_key"],
                "source_job_id": (int(row["source_job_id"]) if row["source_job_id"] is not None else None),
                "status": str(row["status"]),
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

    def list_jobs(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        event_type: str | None = None,
        channel_type: str | None = None,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(500, int(limit)))
        where_parts: list[str] = []
        params: list[Any] = []
        if status:
            where_parts.append("j.status = ?")
            params.append(str(status))
        if event_type:
            where_parts.append("j.event_type = ?")
            params.append(str(event_type))
        if channel_type:
            where_parts.append("c.channel_type = ?")
            params.append(str(channel_type).strip().lower())

        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        conn = self._connect()
        try:
            rows = conn.execute(
                f"""
                SELECT
                    j.job_id,
                    j.channel_id,
                    c.channel_type,
                    c.name AS channel_name,
                    j.event_type,
                    j.payload_json,
                    j.recipient_user_id,
                    j.recipient_username,
                    j.recipient_address,
                    j.dedupe_key,
                    j.source_job_id,
                    j.status,
                    j.attempts,
                    j.max_attempts,
                    j.last_error,
                    j.created_at_ms,
                    j.sent_at_ms,
                    j.next_retry_at_ms,
                    j.read_at_ms
                FROM notification_jobs j
                LEFT JOIN notification_channels c ON c.channel_id = j.channel_id
                {where_sql}
                ORDER BY j.created_at_ms DESC
                LIMIT ?
                """,
                (*params, lim),
            ).fetchall()
            return [
                {
                    "job_id": int(row["job_id"]),
                    "channel_id": str(row["channel_id"]),
                    "channel_type": (str(row["channel_type"]) if row["channel_type"] is not None else None),
                    "channel_name": (str(row["channel_name"]) if row["channel_name"] is not None else None),
                    "event_type": str(row["event_type"]),
                    "payload": from_json_text(row["payload_json"]) or {},
                    "recipient_user_id": row["recipient_user_id"],
                    "recipient_username": row["recipient_username"],
                    "recipient_address": row["recipient_address"],
                    "dedupe_key": row["dedupe_key"],
                    "source_job_id": (int(row["source_job_id"]) if row["source_job_id"] is not None else None),
                    "status": str(row["status"]),
                    "attempts": int(row["attempts"] or 0),
                    "max_attempts": int(row["max_attempts"] or 0),
                    "last_error": row["last_error"],
                    "created_at_ms": int(row["created_at_ms"] or 0),
                    "sent_at_ms": (int(row["sent_at_ms"]) if row["sent_at_ms"] is not None else None),
                    "next_retry_at_ms": (int(row["next_retry_at_ms"]) if row["next_retry_at_ms"] is not None else None),
                    "read_at_ms": (int(row["read_at_ms"]) if row["read_at_ms"] is not None else None),
                }
                for row in rows
            ]
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
        conn = self._connect()
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
        finally:
            conn.close()
        return self.get_job(int(row["job_id"]))

    def reset_job_for_retry(self, *, job_id: int) -> dict[str, Any]:
        conn = self._connect()
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
        conn = self._connect()
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
        conn = self._connect()
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
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT
                    j.job_id,
                    j.channel_id,
                    c.channel_type,
                    c.name AS channel_name,
                    j.event_type,
                    j.payload_json,
                    j.recipient_user_id,
                    j.recipient_username,
                    j.recipient_address,
                    j.dedupe_key,
                    j.source_job_id,
                    j.status,
                    j.attempts,
                    j.max_attempts,
                    j.last_error,
                    j.created_at_ms,
                    j.sent_at_ms,
                    j.next_retry_at_ms,
                    j.read_at_ms
                FROM notification_jobs j
                LEFT JOIN notification_channels c ON c.channel_id = j.channel_id
                WHERE j.status = 'queued'
                  AND (j.next_retry_at_ms IS NULL OR j.next_retry_at_ms <= ?)
                  AND j.attempts < j.max_attempts
                ORDER BY j.created_at_ms ASC
                LIMIT ?
                """,
                (now_ms, lim),
            ).fetchall()
            return [
                {
                    "job_id": int(row["job_id"]),
                    "channel_id": str(row["channel_id"]),
                    "channel_type": (str(row["channel_type"]) if row["channel_type"] is not None else None),
                    "channel_name": (str(row["channel_name"]) if row["channel_name"] is not None else None),
                    "event_type": str(row["event_type"]),
                    "payload": from_json_text(row["payload_json"]) or {},
                    "recipient_user_id": row["recipient_user_id"],
                    "recipient_username": row["recipient_username"],
                    "recipient_address": row["recipient_address"],
                    "dedupe_key": row["dedupe_key"],
                    "source_job_id": (int(row["source_job_id"]) if row["source_job_id"] is not None else None),
                    "status": str(row["status"]),
                    "attempts": int(row["attempts"] or 0),
                    "max_attempts": int(row["max_attempts"] or 0),
                    "last_error": row["last_error"],
                    "created_at_ms": int(row["created_at_ms"] or 0),
                    "sent_at_ms": (int(row["sent_at_ms"]) if row["sent_at_ms"] is not None else None),
                    "next_retry_at_ms": (int(row["next_retry_at_ms"]) if row["next_retry_at_ms"] is not None else None),
                    "read_at_ms": (int(row["read_at_ms"]) if row["read_at_ms"] is not None else None),
                }
                for row in rows
            ]
        finally:
            conn.close()

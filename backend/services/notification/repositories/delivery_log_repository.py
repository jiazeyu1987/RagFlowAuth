from __future__ import annotations

import time

from .common import ConnectFactory


class NotificationDeliveryLogRepository:
    def __init__(self, connect: ConnectFactory):
        self._connect = connect

    def add_delivery_log(self, *, job_id: int, channel_id: str, status: str, error: str | None = None) -> None:
        now_ms = int(time.time() * 1000)
        conn = self._connect()
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

    def list_delivery_logs(self, *, job_id: int, limit: int = 50) -> list[dict[str, object]]:
        lim = max(1, min(500, int(limit)))
        conn = self._connect()
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

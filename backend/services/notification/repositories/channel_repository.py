from __future__ import annotations

import time
from typing import Any

from .common import ConnectFactory, from_json_text, to_json_text


class NotificationChannelRepository:
    def __init__(self, connect: ConnectFactory):
        self._connect = connect

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
        config_json = to_json_text(config or {})
        conn = self._connect()
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
        conn = self._connect()
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
                "channel_id": str(row["channel_id"]),
                "channel_type": str(row["channel_type"]),
                "name": str(row["name"]),
                "enabled": bool(row["enabled"]),
                "config": from_json_text(row["config_json"]) or {},
                "created_at_ms": int(row["created_at_ms"] or 0),
                "updated_at_ms": int(row["updated_at_ms"] or 0),
            }
        finally:
            conn.close()

    def list_channels(self, *, enabled_only: bool = False) -> list[dict[str, Any]]:
        where_sql = "WHERE enabled = 1" if enabled_only else ""
        conn = self._connect()
        try:
            rows = conn.execute(
                f"""
                SELECT channel_id, channel_type, name, enabled, config_json, created_at_ms, updated_at_ms
                FROM notification_channels
                {where_sql}
                ORDER BY updated_at_ms DESC
                """
            ).fetchall()
            return [
                {
                    "channel_id": str(row["channel_id"]),
                    "channel_type": str(row["channel_type"]),
                    "name": str(row["name"]),
                    "enabled": bool(row["enabled"]),
                    "config": from_json_text(row["config_json"]) or {},
                    "created_at_ms": int(row["created_at_ms"] or 0),
                    "updated_at_ms": int(row["updated_at_ms"] or 0),
                }
                for row in rows
            ]
        finally:
            conn.close()

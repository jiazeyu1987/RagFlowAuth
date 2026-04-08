from __future__ import annotations

import time

from backend.services.notification.event_catalog import AVAILABLE_CHANNEL_TYPES

from .common import ConnectFactory, from_json_text, to_json_text


class NotificationEventRuleRepository:
    def __init__(self, connect: ConnectFactory):
        self._connect = connect

    def get_event_rule(self, event_type: str) -> dict[str, object] | None:
        normalized_event_type = str(event_type or "").strip()
        if not normalized_event_type:
            return None
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT event_type, enabled_channel_types_json, created_at_ms, updated_at_ms
                FROM notification_event_rules
                WHERE event_type = ?
                """,
                (normalized_event_type,),
            ).fetchone()
            if not row:
                return None
            return {
                "event_type": str(row["event_type"]),
                "enabled_channel_types": list(from_json_text(row["enabled_channel_types_json"]) or []),
                "created_at_ms": int(row["created_at_ms"] or 0),
                "updated_at_ms": int(row["updated_at_ms"] or 0),
            }
        finally:
            conn.close()

    def list_event_rules(self) -> list[dict[str, object]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT event_type, enabled_channel_types_json, created_at_ms, updated_at_ms
                FROM notification_event_rules
                ORDER BY event_type ASC
                """
            ).fetchall()
            return [
                {
                    "event_type": str(row["event_type"]),
                    "enabled_channel_types": list(from_json_text(row["enabled_channel_types_json"]) or []),
                    "created_at_ms": int(row["created_at_ms"] or 0),
                    "updated_at_ms": int(row["updated_at_ms"] or 0),
                }
                for row in rows
            ]
        finally:
            conn.close()

    def upsert_event_rule(
        self,
        *,
        event_type: str,
        enabled_channel_types: list[str] | tuple[str, ...] | set[str],
    ) -> dict[str, object]:
        normalized_event_type = str(event_type or "").strip()
        if not normalized_event_type:
            raise ValueError("notification_event_type_required")

        normalized_types: list[str] = []
        seen: set[str] = set()
        for item in enabled_channel_types or []:
            channel_type = str(item or "").strip().lower()
            if not channel_type:
                continue
            if channel_type not in AVAILABLE_CHANNEL_TYPES:
                raise ValueError("invalid_channel_type")
            if channel_type in seen:
                continue
            seen.add(channel_type)
            normalized_types.append(channel_type)

        now_ms = int(time.time() * 1000)
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO notification_event_rules (
                    event_type, enabled_channel_types_json, created_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(event_type) DO UPDATE SET
                    enabled_channel_types_json = excluded.enabled_channel_types_json,
                    updated_at_ms = excluded.updated_at_ms
                """,
                (normalized_event_type, to_json_text(normalized_types), now_ms, now_ms),
            )
            conn.commit()
        finally:
            conn.close()

        item = self.get_event_rule(normalized_event_type)
        if not item:
            raise RuntimeError("notification_event_rule_upsert_failed")
        return item

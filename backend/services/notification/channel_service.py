from __future__ import annotations

from typing import Any

from .audit import emit_notification_audit
from .store import NotificationStore


class NotificationChannelService:
    def __init__(self, *, store: NotificationStore, audit_log_manager: Any | None = None):
        self._store = store
        self._audit_log_manager = audit_log_manager

    def upsert_channel(
        self,
        *,
        channel_id: str,
        channel_type: str,
        name: str,
        enabled: bool,
        config: dict[str, Any] | None,
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        before = self._store.get_channel(str(channel_id or "").strip())
        item = self._store.upsert_channel(
            channel_id=channel_id,
            channel_type=channel_type,
            name=name,
            enabled=enabled,
            config=config,
        )
        emit_notification_audit(
            self._audit_log_manager,
            action="notification_channel_upsert",
            event_type=("create" if before is None else "update"),
            resource_type="notification_channel",
            resource_id=str(item["channel_id"]),
            before=before,
            after=item,
            meta={"channel_type": item.get("channel_type"), "enabled": bool(item.get("enabled"))},
            audit=audit,
        )
        return item

    def list_channels(self, *, enabled_only: bool = False) -> list[dict[str, Any]]:
        return self._store.list_channels(enabled_only=enabled_only)

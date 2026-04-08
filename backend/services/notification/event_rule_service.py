from __future__ import annotations

from typing import Any

from .audit import emit_notification_audit
from .event_catalog import AVAILABLE_CHANNEL_TYPES, SUPPORTED_EVENT_TYPES, list_event_groups
from .helpers import normalize_channel_types
from .store import NotificationStore


class NotificationEventRuleService:
    def __init__(self, *, store: NotificationStore, audit_log_manager: Any | None = None):
        self._store = store
        self._audit_log_manager = audit_log_manager

    def list_event_rules(self) -> dict[str, Any]:
        self.ensure_event_rules_seeded()
        rules_by_type = {str(item["event_type"]): item for item in self._store.list_event_rules()}
        enabled_channel_config = self.enabled_channel_config_by_type()

        groups: list[dict[str, Any]] = []
        count = 0
        for group in list_event_groups():
            group_items: list[dict[str, Any]] = []
            for item in group.get("items") or []:
                event_type = str(item["event_type"])
                stored_rule = rules_by_type.get(event_type) or {}
                raw_enabled_channel_types = (
                    stored_rule.get("enabled_channel_types")
                    if stored_rule
                    else self.default_rule_channel_types()
                )
                enabled_channel_types = normalize_channel_types(raw_enabled_channel_types)
                group_items.append(
                    {
                        "group_key": str(group["group_key"]),
                        "group_label": str(group["group_label"]),
                        "event_type": event_type,
                        "event_label": str(item["event_label"]),
                        "enabled_channel_types": enabled_channel_types,
                        "available_channel_types": list(AVAILABLE_CHANNEL_TYPES),
                        "has_enabled_channel_config_by_type": dict(enabled_channel_config),
                    }
                )
                count += 1
            groups.append(
                {
                    "group_key": str(group["group_key"]),
                    "group_label": str(group["group_label"]),
                    "items": group_items,
                }
            )
        return {"groups": groups, "count": count}

    def upsert_event_rules(
        self,
        *,
        items: list[dict[str, Any]],
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.ensure_event_rules_seeded()
        for item in items or []:
            event_type = str((item or {}).get("event_type") or "").strip()
            if event_type not in SUPPORTED_EVENT_TYPES:
                raise ValueError("notification_event_type_unsupported")
            enabled_channel_types = normalize_channel_types((item or {}).get("enabled_channel_types") or [])
            before = self._store.get_event_rule(event_type)
            updated = self._store.upsert_event_rule(
                event_type=event_type,
                enabled_channel_types=enabled_channel_types,
            )
            emit_notification_audit(
                self._audit_log_manager,
                action="notification_event_rule_upsert",
                event_type=("create" if before is None else "update"),
                resource_type="notification_event_rule",
                resource_id=event_type,
                before=before,
                after=updated,
                meta={"event_type": event_type, "enabled_channel_types": enabled_channel_types},
                audit=audit,
            )
        return self.list_event_rules()

    def get_event_rule(self, event_type: str) -> dict[str, object] | None:
        return self._store.get_event_rule(event_type)

    def ensure_event_rules_seeded(self) -> None:
        existing_event_types = {str(item["event_type"]) for item in self._store.list_event_rules()}
        default_channel_types = self.default_rule_channel_types()
        for event_type in SUPPORTED_EVENT_TYPES:
            if event_type in existing_event_types:
                continue
            self._store.upsert_event_rule(
                event_type=event_type,
                enabled_channel_types=default_channel_types,
            )

    def default_rule_channel_types(self) -> list[str]:
        enabled_channel_config = self.enabled_channel_config_by_type()
        items = ["in_app"]
        for channel_type_name in ("email", "dingtalk"):
            if enabled_channel_config.get(channel_type_name):
                items.append(channel_type_name)
        return normalize_channel_types(items)

    def enabled_channels_by_type(self) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {channel_type_name: [] for channel_type_name in AVAILABLE_CHANNEL_TYPES}
        for channel in self._store.list_channels(enabled_only=True):
            channel_type_name = str(channel.get("channel_type") or "").strip().lower()
            if channel_type_name in out:
                out[channel_type_name].append(channel)
        return out

    def enabled_channel_config_by_type(self) -> dict[str, bool]:
        return {
            channel_type_name: bool(items)
            for channel_type_name, items in self.enabled_channels_by_type().items()
        }

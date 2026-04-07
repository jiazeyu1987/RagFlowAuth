from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from .dingtalk_adapter import DingTalkNotificationAdapter
from .email_adapter import EmailNotificationAdapter
from .event_catalog import AVAILABLE_CHANNEL_TYPES, SUPPORTED_EVENT_TYPES, list_event_groups
from .store import NotificationStore

logger = logging.getLogger(__name__)


@dataclass
class NotificationManagerError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class NotificationManager:
    def __init__(
        self,
        *,
        store: NotificationStore,
        email_adapter: Any | None = None,
        dingtalk_adapter: Any | None = None,
        audit_log_manager: Any | None = None,
        retry_interval_seconds: int = 60,
    ):
        self._store = store
        self._email_adapter = email_adapter or EmailNotificationAdapter()
        self._dingtalk_adapter = dingtalk_adapter or DingTalkNotificationAdapter()
        self._audit_log_manager = audit_log_manager
        self._retry_interval_seconds = max(1, int(retry_interval_seconds))

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
        try:
            item = self._store.upsert_channel(
                channel_id=channel_id,
                channel_type=channel_type,
                name=name,
                enabled=enabled,
                config=config,
            )
        except ValueError as e:
            raise NotificationManagerError(str(e), status_code=400) from e

        self._emit_audit(
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

    def rebuild_dingtalk_recipient_map_from_org(
        self,
        *,
        channel_id: str,
        user_store: Any,
        org_directory_store: Any,
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        channel = self._store.get_channel(str(channel_id or "").strip())
        if not channel:
            raise NotificationManagerError("notification_channel_not_found", status_code=404)
        if str(channel.get("channel_type") or "").strip().lower() != "dingtalk":
            raise NotificationManagerError("notification_channel_not_dingtalk", status_code=400)

        config = channel.get("config") or {}
        if not isinstance(config, dict):
            raise NotificationManagerError("notification_channel_config_invalid", status_code=400)

        self._validate_dingtalk_channel_access(channel=channel)

        org_employees = self._list_org_employees_for_recipient_map_rebuild(org_directory_store)
        recipient_map: dict[str, str] = {}
        recipient_directory, invalid_org_users = self._build_dingtalk_recipient_directory(org_employees)
        if invalid_org_users:
            raise NotificationManagerError("notification_dingtalk_org_directory_invalid", status_code=400)
        user_binding_summary = self._sync_employee_user_ids_from_org(
            user_store=user_store,
            org_employees=org_employees,
        )

        updated_config = dict(config)
        updated_config["recipient_map"] = recipient_map
        updated_config["recipient_directory"] = recipient_directory
        updated_channel = self._store.upsert_channel(
            channel_id=str(channel["channel_id"]),
            channel_type=str(channel["channel_type"]),
            name=str(channel["name"]),
            enabled=bool(channel.get("enabled")),
            config=updated_config,
        )

        summary = {
            "channel_id": str(updated_channel["channel_id"]),
            "org_user_count": len(org_employees),
            "directory_entry_count": len(recipient_directory),
            "alias_entry_count": len(recipient_map),
            "invalid_org_user_count": len(invalid_org_users),
            "invalid_org_users": invalid_org_users,
        }
        self._emit_audit(
            action="notification_channel_recipient_map_rebuild",
            event_type="update",
            resource_type="notification_channel",
            resource_id=str(updated_channel["channel_id"]),
            before=channel,
            after=updated_channel,
            meta={**summary, **user_binding_summary},
            audit=audit,
        )
        return summary

    def list_jobs(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        event_type: str | None = None,
        channel_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._store.list_jobs(limit=limit, status=status, event_type=event_type, channel_type=channel_type)

    def list_delivery_logs(self, *, job_id: int, limit: int = 50) -> list[dict[str, Any]]:
        return self._store.list_delivery_logs(job_id=int(job_id), limit=limit)

    def list_event_rules(self) -> dict[str, Any]:
        self._ensure_event_rules_seeded()
        rules_by_type = {str(item["event_type"]): item for item in self._store.list_event_rules()}
        enabled_channel_config = self._enabled_channel_config_by_type()

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
                    else self._default_rule_channel_types()
                )
                enabled_channel_types = self._normalize_channel_types(raw_enabled_channel_types)
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
        self._ensure_event_rules_seeded()
        for item in items or []:
            event_type = str((item or {}).get("event_type") or "").strip()
            if event_type not in SUPPORTED_EVENT_TYPES:
                raise NotificationManagerError("notification_event_type_unsupported", status_code=400)
            enabled_channel_types = self._normalize_channel_types((item or {}).get("enabled_channel_types") or [])
            before = self._store.get_event_rule(event_type)
            updated = self._store.upsert_event_rule(
                event_type=event_type,
                enabled_channel_types=enabled_channel_types,
            )
            self._emit_audit(
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

    def notify_event(
        self,
        *,
        event_type: str,
        payload: dict[str, Any] | None,
        recipients: list[dict[str, Any]] | None,
        dedupe_key: str | None = None,
        allow_duplicate: bool = False,
        max_attempts: int = 3,
        channel_types: list[str] | tuple[str, ...] | set[str] | None = None,
        audit: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        event_type = str(event_type or "").strip()
        if not event_type:
            raise NotificationManagerError("notification_event_type_required", status_code=400)
        if event_type not in SUPPORTED_EVENT_TYPES:
            raise NotificationManagerError("notification_event_type_unsupported", status_code=400)

        self._ensure_event_rules_seeded()
        event_rule = self._store.get_event_rule(event_type)
        if event_rule is None:
            raise NotificationManagerError("notification_event_rule_not_found", status_code=500)

        rule_channel_types = self._normalize_channel_types(event_rule.get("enabled_channel_types") or [])
        caller_channel_types = (
            self._normalize_channel_types(channel_types or [])
            if channel_types is not None
            else None
        )
        if caller_channel_types is None:
            effective_channel_types = list(rule_channel_types)
        else:
            requested_set = set(caller_channel_types)
            effective_channel_types = [item for item in rule_channel_types if item in requested_set]
        if not effective_channel_types:
            return []

        enabled_channels_by_type = self._enabled_channels_by_type()
        missing_channel_types = [
            channel_type_name
            for channel_type_name in effective_channel_types
            if not enabled_channels_by_type.get(channel_type_name)
        ]
        if missing_channel_types:
            detail = ",".join(missing_channel_types)
            raise NotificationManagerError(
                f"notification_channel_not_configured:{detail}",
                status_code=400,
            )

        channels: list[dict[str, Any]] = []
        for channel_type_name in effective_channel_types:
            channels.extend(enabled_channels_by_type.get(channel_type_name) or [])

        normalized_recipients = self._normalize_recipients(recipients)
        if not normalized_recipients:
            raise NotificationManagerError("notification_recipients_required", status_code=400)

        unresolved: list[str] = []
        dispatch_targets: list[tuple[dict[str, Any], dict[str, Any], str]] = []
        for channel in channels:
            for recipient in normalized_recipients:
                address = self._resolve_recipient_address(channel=channel, recipient=recipient)
                if not address:
                    unresolved.append(
                        f"{channel['channel_id']}:{recipient.get('user_id') or recipient.get('username') or 'unknown'}"
                    )
                    continue
                dispatch_targets.append((channel, recipient, address))

        if unresolved:
            detail = ",".join(unresolved[:10])
            raise NotificationManagerError(
                f"notification_recipient_unresolved:{detail}" if detail else "notification_recipient_unresolved",
                status_code=400,
            )

        jobs: list[dict[str, Any]] = []
        for channel, recipient, address in dispatch_targets:
            existing = None
            if not allow_duplicate:
                existing = self._store.find_duplicate_job(
                    channel_id=str(channel["channel_id"]),
                    event_type=event_type,
                    recipient_user_id=recipient.get("user_id"),
                    dedupe_key=dedupe_key,
                )
            if existing is not None:
                jobs.append(existing)
                continue

            job = self._store.create_job(
                channel_id=str(channel["channel_id"]),
                event_type=event_type,
                payload=payload or {},
                recipient_user_id=recipient.get("user_id"),
                recipient_username=recipient.get("username"),
                recipient_address=address,
                dedupe_key=dedupe_key,
                max_attempts=int(max_attempts),
            )
            self._store.add_delivery_log(
                job_id=int(job["job_id"]),
                channel_id=str(channel["channel_id"]),
                status="queued",
                error=None,
            )
            self._emit_audit(
                action="notification_job_enqueue",
                event_type="create",
                resource_type="notification_job",
                resource_id=str(job["job_id"]),
                before=None,
                after=job,
                meta={
                    "channel_id": channel.get("channel_id"),
                    "channel_type": channel.get("channel_type"),
                    "event_type": event_type,
                    "recipient_user_id": recipient.get("user_id"),
                    "recipient_username": recipient.get("username"),
                    "dedupe_key": dedupe_key,
                },
                audit=audit,
            )
            jobs.append(job)
        return jobs

    def dispatch_job(self, *, job_id: int, audit: dict[str, Any] | None = None) -> dict[str, Any]:
        job = self._store.get_job(int(job_id))
        if not job:
            raise NotificationManagerError("notification_job_not_found", status_code=404)
        channel = self._store.get_channel(str(job["channel_id"]))
        if not channel:
            raise NotificationManagerError("notification_channel_not_found", status_code=404)

        before = dict(job)
        if not bool(channel.get("enabled")):
            error = "notification_channel_disabled"
            self._store.add_delivery_log(
                job_id=int(job["job_id"]),
                channel_id=str(channel["channel_id"]),
                status="failed",
                error=error,
            )
            updated = self._store.mark_job_failed(
                job_id=int(job["job_id"]),
                error=error,
                retry_interval_seconds=self._retry_interval_seconds,
            )
            self._emit_audit(
                action="notification_job_dispatch",
                event_type="failed",
                resource_type="notification_job",
                resource_id=str(updated["job_id"]),
                before=before,
                after=updated,
                meta={"channel_type": channel.get("channel_type"), "error": error},
                audit=audit,
            )
            return updated

        if str(channel.get("channel_type") or "").strip().lower() == "in_app":
            self._store.add_delivery_log(
                job_id=int(job["job_id"]),
                channel_id=str(channel["channel_id"]),
                status="sent",
                error=None,
            )
            updated = self._store.mark_job_sent(job_id=int(job["job_id"]))
            self._emit_audit(
                action="notification_job_dispatch",
                event_type="sent",
                resource_type="notification_job",
                resource_id=str(updated["job_id"]),
                before=before,
                after=updated,
                meta={"channel_type": "in_app"},
                audit=audit,
            )
            return updated

        adapter = self._resolve_adapter(str(channel["channel_type"]))
        try:
            adapter.send(
                channel=channel,
                event_type=str(job["event_type"]),
                payload=job.get("payload") or {},
                recipient={
                    "user_id": job.get("recipient_user_id"),
                    "username": job.get("recipient_username"),
                    "address": job.get("recipient_address"),
                },
            )
            self._store.add_delivery_log(
                job_id=int(job["job_id"]),
                channel_id=str(channel["channel_id"]),
                status="sent",
                error=None,
            )
            updated = self._store.mark_job_sent(job_id=int(job["job_id"]))
            self._emit_audit(
                action="notification_job_dispatch",
                event_type="sent",
                resource_type="notification_job",
                resource_id=str(updated["job_id"]),
                before=before,
                after=updated,
                meta={"channel_type": channel.get("channel_type")},
                audit=audit,
            )
            return updated
        except Exception as e:
            err = str(e) or e.__class__.__name__
            logger.warning(
                "Notification dispatch failed: job_id=%s channel_id=%s err=%s",
                job["job_id"],
                channel["channel_id"],
                err,
            )
            self._store.add_delivery_log(
                job_id=int(job["job_id"]),
                channel_id=str(channel["channel_id"]),
                status="failed",
                error=err,
            )
            updated = self._store.mark_job_failed(
                job_id=int(job["job_id"]),
                error=err,
                retry_interval_seconds=self._retry_interval_seconds,
            )
            self._emit_audit(
                action="notification_job_dispatch",
                event_type="failed",
                resource_type="notification_job",
                resource_id=str(updated["job_id"]),
                before=before,
                after=updated,
                meta={"channel_type": channel.get("channel_type"), "error": err},
                audit=audit,
            )
            return updated

    def dispatch_pending(self, *, limit: int = 100, audit: dict[str, Any] | None = None) -> dict[str, Any]:
        jobs = self._store.list_dispatchable_jobs(limit=limit)
        items: list[dict[str, Any]] = []
        for job in jobs:
            try:
                updated = self.dispatch_job(job_id=int(job["job_id"]), audit=audit)
                items.append(
                    {
                        "job_id": int(updated["job_id"]),
                        "status": str(updated["status"]),
                        "attempts": int(updated["attempts"]),
                        "last_error": updated.get("last_error"),
                    }
                )
            except Exception as e:
                items.append(
                    {
                        "job_id": int(job["job_id"]),
                        "status": "error",
                        "attempts": int(job.get("attempts") or 0),
                        "last_error": str(e),
                    }
                )
        return {"total": len(items), "items": items}

    def retry_job(self, *, job_id: int, audit: dict[str, Any] | None = None) -> dict[str, Any]:
        job = self._store.get_job(int(job_id))
        if not job:
            raise NotificationManagerError("notification_job_not_found", status_code=404)
        if str(job["status"]) == "sent":
            raise NotificationManagerError("notification_job_already_sent", status_code=400)

        self._store.reset_job_for_retry(job_id=int(job_id))
        reset_job = self._store.get_job(int(job_id))
        if not reset_job:
            raise NotificationManagerError("notification_job_not_found_after_retry_reset", status_code=500)
        self._store.add_delivery_log(
            job_id=int(reset_job["job_id"]),
            channel_id=str(reset_job["channel_id"]),
            status="queued",
            error=None,
        )

        updated = self.dispatch_job(job_id=int(job_id), audit=audit)
        self._emit_audit(
            action="notification_job_retry",
            event_type="update",
            resource_type="notification_job",
            resource_id=str(updated["job_id"]),
            before=job,
            after=updated,
            meta={"from_status": job.get("status"), "to_status": updated.get("status")},
            audit=audit,
        )
        return updated

    def resend_job(self, *, job_id: int, audit: dict[str, Any] | None = None) -> dict[str, Any]:
        source = self._store.get_job(int(job_id))
        if not source:
            raise NotificationManagerError("notification_job_not_found", status_code=404)
        dedupe_key = str(source.get("dedupe_key") or f"job-{job_id}")
        cloned = self._store.clone_job_for_resend(
            job_id=int(job_id),
            dedupe_key=f"{dedupe_key}:manual-resend:{int(time.time() * 1000)}",
        )
        self._store.add_delivery_log(
            job_id=int(cloned["job_id"]),
            channel_id=str(cloned["channel_id"]),
            status="queued",
            error=None,
        )
        self._emit_audit(
            action="notification_job_enqueue",
            event_type="create",
            resource_type="notification_job",
            resource_id=str(cloned["job_id"]),
            before=None,
            after=cloned,
            meta={
                "source_job_id": source.get("job_id"),
                "channel_id": cloned.get("channel_id"),
                "event_type": cloned.get("event_type"),
            },
            audit=audit,
        )

        updated = self.dispatch_job(job_id=int(cloned["job_id"]), audit=audit)
        self._emit_audit(
            action="notification_job_resend",
            event_type="create",
            resource_type="notification_job",
            resource_id=str(updated["job_id"]),
            before=source,
            after=updated,
            meta={"source_job_id": source.get("job_id"), "new_job_id": updated.get("job_id")},
            audit=audit,
        )
        return updated

    def list_inbox(
        self,
        *,
        recipient_user_id: str,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> dict[str, Any]:
        try:
            total, unread_count, items = self._store.list_inbox(
                recipient_user_id=recipient_user_id,
                limit=limit,
                offset=offset,
                unread_only=unread_only,
            )
        except ValueError as e:
            raise NotificationManagerError(str(e), status_code=400) from e
        return {"total": total, "unread_count": unread_count, "items": items}

    def update_inbox_read_state(
        self,
        *,
        job_id: int,
        recipient_user_id: str,
        read: bool,
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            before = self._ensure_owned_in_app_job(job_id=job_id, recipient_user_id=recipient_user_id)
            updated = self._store.set_inbox_read_state(
                job_id=int(job_id),
                recipient_user_id=recipient_user_id,
                read=bool(read),
            )
        except ValueError as e:
            raise NotificationManagerError(str(e), status_code=400) from e
        if not updated:
            raise NotificationManagerError("notification_message_not_found", status_code=404)

        self._store.add_delivery_log(
            job_id=int(updated["job_id"]),
            channel_id=str(updated["channel_id"]),
            status=("read" if bool(read) else "unread"),
            error=None,
        )
        self._emit_audit(
            action="notification_inbox_read_state_update",
            event_type="update",
            resource_type="notification_job",
            resource_id=str(updated["job_id"]),
            before=before,
            after=updated,
            meta={"read": bool(read)},
            audit=audit,
        )
        return updated

    def mark_all_inbox_read(
        self,
        *,
        recipient_user_id: str,
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        recipient_user_id = str(recipient_user_id or "").strip()
        if not recipient_user_id:
            raise NotificationManagerError("recipient_user_id_required", status_code=400)

        unread_ids = self._collect_unread_inbox_job_ids(recipient_user_id=recipient_user_id)
        try:
            changed = self._store.mark_all_inbox_read(recipient_user_id=recipient_user_id)
        except ValueError as e:
            raise NotificationManagerError(str(e), status_code=400) from e

        for job_id in unread_ids:
            job = self._store.get_job(int(job_id))
            if not job:
                continue
            self._store.add_delivery_log(
                job_id=int(job["job_id"]),
                channel_id=str(job["channel_id"]),
                status="read",
                error=None,
            )

        self._emit_audit(
            action="notification_inbox_mark_all_read",
            event_type="update",
            resource_type="notification_inbox",
            resource_id=str(recipient_user_id),
            before=None,
            after={"updated_count": int(changed)},
            meta={"updated_count": int(changed)},
            audit=audit,
        )
        return {"updated_count": int(changed)}

    def _resolve_adapter(self, channel_type: str):
        kind = str(channel_type or "").strip().lower()
        if kind == "email":
            return self._email_adapter
        if kind == "dingtalk":
            return self._dingtalk_adapter
        raise NotificationManagerError("notification_channel_type_unsupported", status_code=400)

    def _collect_unread_inbox_job_ids(self, *, recipient_user_id: str) -> list[int]:
        out: list[int] = []
        offset = 0
        limit = 500
        while True:
            total, _, items = self._store.list_inbox(
                recipient_user_id=recipient_user_id,
                limit=limit,
                offset=offset,
                unread_only=True,
            )
            for item in items:
                out.append(int(item["job_id"]))
            offset += len(items)
            if not items or offset >= total:
                break
        return out

    def _ensure_owned_in_app_job(self, *, job_id: int, recipient_user_id: str) -> dict[str, Any]:
        job = self._store.get_job(int(job_id))
        if not job:
            raise NotificationManagerError("notification_message_not_found", status_code=404)

        channel = self._store.get_channel(str(job["channel_id"]))
        if not channel:
            raise NotificationManagerError("notification_channel_not_found", status_code=404)
        if str(channel.get("channel_type") or "").strip().lower() != "in_app":
            raise NotificationManagerError("notification_message_not_found", status_code=404)
        if str(job.get("status") or "") != "sent":
            raise NotificationManagerError("notification_message_not_available", status_code=409)
        if str(job.get("recipient_user_id") or "").strip() != str(recipient_user_id or "").strip():
            raise NotificationManagerError("notification_message_not_found", status_code=404)
        return job

    def _validate_dingtalk_channel_access(self, *, channel: dict[str, Any]) -> None:
        adapter = self._resolve_adapter("dingtalk")
        validate_channel = getattr(adapter, "validate_channel", None)
        if not callable(validate_channel):
            raise NotificationManagerError("notification_dingtalk_validation_unavailable", status_code=500)
        try:
            validate_channel(channel=channel)
        except NotificationManagerError:
            raise
        except RuntimeError as exc:
            raise NotificationManagerError(str(exc), status_code=400) from exc

    @staticmethod
    def _list_org_employees_for_recipient_map_rebuild(org_directory_store: Any) -> list[Any]:
        list_employees = getattr(org_directory_store, "list_employees", None)
        if not callable(list_employees):
            raise NotificationManagerError("notification_org_directory_unavailable", status_code=500)
        employees = list(list_employees() or [])
        employees.sort(
            key=lambda item: (
                NotificationManager._string_attr(item, "employee_user_id"),
                NotificationManager._string_attr(item, "name"),
                NotificationManager._optional_int_attr(item, "company_id") or 0,
                NotificationManager._optional_int_attr(item, "department_id") or 0,
            )
        )
        return employees

    @staticmethod
    def _normalize_existing_recipient_map(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, str] = {}
        for raw_key, raw_target in value.items():
            key = str(raw_key or "").strip()
            target = str(raw_target or "").strip()
            if not key or not target:
                continue
            normalized[key] = target
        return normalized

    @staticmethod
    def _build_dingtalk_recipient_directory(org_employees: list[Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
        directory: dict[str, dict[str, Any]] = {}
        invalid_org_users: list[dict[str, str]] = []
        duplicate_user_ids: set[str] = set()

        for employee in org_employees:
            employee_user_id = NotificationManager._string_attr(employee, "employee_user_id")
            full_name = NotificationManager._string_attr(employee, "name")
            if not employee_user_id:
                invalid_org_users.append(
                    {
                        "employee_user_id": "",
                        "full_name": full_name,
                        "reason": "employee_user_id_missing",
                    }
                )
                continue
            if employee_user_id in directory:
                duplicate_user_ids.add(employee_user_id)
                continue
            directory[employee_user_id] = {
                "full_name": full_name,
                "company_id": NotificationManager._optional_int_attr(employee, "company_id"),
                "department_id": NotificationManager._optional_int_attr(employee, "department_id"),
            }

        if duplicate_user_ids:
            duplicate_items: list[dict[str, str]] = []
            seen_duplicates: set[tuple[str, str]] = set()
            for employee in org_employees:
                employee_user_id = NotificationManager._string_attr(employee, "employee_user_id")
                if employee_user_id not in duplicate_user_ids:
                    continue
                full_name = NotificationManager._string_attr(employee, "name")
                key = (employee_user_id, full_name)
                if key in seen_duplicates:
                    continue
                seen_duplicates.add(key)
                duplicate_items.append(
                    {
                        "employee_user_id": employee_user_id,
                        "full_name": full_name,
                        "reason": "employee_user_id_duplicate",
                    }
                )
                directory.pop(employee_user_id, None)
            invalid_org_users.extend(duplicate_items)

        invalid_org_users.sort(
            key=lambda item: (
                str(item.get("reason") or ""),
                str(item.get("full_name") or ""),
                str(item.get("employee_user_id") or ""),
            )
        )
        return directory, invalid_org_users

    @classmethod
    def _sync_employee_user_ids_from_org(
        cls,
        *,
        user_store: Any,
        org_employees: list[Any],
    ) -> dict[str, int]:
        list_users = getattr(user_store, "list_users", None)
        sync_employee_user_ids = getattr(user_store, "sync_employee_user_ids", None)
        if not callable(list_users) or not callable(sync_employee_user_ids):
            raise NotificationManagerError("notification_user_store_unavailable", status_code=500)

        users = list(list_users(status="active", limit=1000000) or [])
        employees_by_name: dict[str, list[Any]] = {}
        for employee in org_employees:
            name = cls._normalized_name(cls._string_attr(employee, "name"))
            if not name:
                continue
            employees_by_name.setdefault(name, []).append(employee)

        assignments: dict[str, str | None] = {}
        matched_user_count = 0
        unmatched_user_count = 0
        for user in users:
            user_id = cls._string_attr(user, "user_id")
            if not user_id:
                continue

            full_name = cls._normalized_name(cls._string_attr(user, "full_name"))
            employee_user_id: str | None = None
            if full_name:
                candidates = list(employees_by_name.get(full_name) or [])
                company_id = cls._optional_int_attr(user, "company_id")
                if company_id is not None:
                    candidates = [
                        item
                        for item in candidates
                        if cls._optional_int_attr(item, "company_id") == company_id
                    ]
                if len(candidates) > 1:
                    department_id = cls._optional_int_attr(user, "department_id")
                    if department_id is not None:
                        candidates = [
                            item
                            for item in candidates
                            if cls._optional_int_attr(item, "department_id") == department_id
                        ]
                if len(candidates) == 1:
                    employee_user_id = cls._string_attr(candidates[0], "employee_user_id") or None

            assignments[user_id] = employee_user_id
            if employee_user_id:
                matched_user_count += 1
            else:
                unmatched_user_count += 1

        sync_employee_user_ids(assignments)
        return {
            "matched_user_count": matched_user_count,
            "unmatched_user_count": unmatched_user_count,
        }

    @staticmethod
    def _normalized_name(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _string_attr(item: Any, field: str) -> str:
        value = getattr(item, field, None)
        if value is None and isinstance(item, dict):
            value = item.get(field)
        return str(value or "").strip()

    @staticmethod
    def _optional_int_attr(item: Any, field: str) -> int | None:
        value = getattr(item, field, None)
        if value is None and isinstance(item, dict):
            value = item.get(field)
        if value is None or str(value).strip() == "":
            return None
        try:
            return int(value)
        except Exception as exc:  # noqa: BLE001
            raise NotificationManagerError(f"notification_invalid_{field}", status_code=500) from exc

    @staticmethod
    def _normalize_recipients(recipients: list[dict[str, Any]] | None) -> list[dict[str, str | None]]:
        normalized: list[dict[str, str | None]] = []
        seen: set[tuple[str, str]] = set()
        for item in recipients or []:
            user_id = str((item or {}).get("user_id") or "").strip() or None
            username = str((item or {}).get("username") or "").strip() or None
            key = (user_id or "", username or "")
            if key == ("", "") or key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "user_id": user_id,
                    "username": username,
                    "employee_user_id": (str(item.get("employee_user_id")).strip() if item.get("employee_user_id") else None),
                    "full_name": (str(item.get("full_name")) if item.get("full_name") else None),
                    "email": (str(item.get("email")).strip() if item.get("email") else None),
                }
            )
        return normalized

    @staticmethod
    def _resolve_recipient_address(*, channel: dict[str, Any], recipient: dict[str, str | None]) -> str | None:
        channel_type = str(channel.get("channel_type") or "").strip().lower()
        if channel_type == "email":
            email = str(recipient.get("email") or "").strip()
            return email or None
        if channel_type == "dingtalk":
            config = channel.get("config") or {}
            recipient_map = config.get("recipient_map")
            if not isinstance(recipient_map, dict):
                recipient_map = {}
            recipient_directory = config.get("recipient_directory")
            if not isinstance(recipient_directory, dict):
                recipient_directory = {}
            user_id = str(recipient.get("user_id") or "").strip()
            username = str(recipient.get("username") or "").strip()
            employee_user_id = str(recipient.get("employee_user_id") or "").strip()
            value = None
            if user_id:
                value = recipient_map.get(user_id)
            if value is None and username:
                value = recipient_map.get(username)
            if value is not None:
                target = str(value or "").strip()
                return target or None
            if employee_user_id and employee_user_id in recipient_directory:
                return employee_user_id
            if user_id and user_id in recipient_directory:
                return user_id
            if username and username in recipient_directory:
                return username
            return None
        if channel_type == "in_app":
            user_id = str(recipient.get("user_id") or "").strip()
            return user_id or None
        return None

    def _emit_audit(
        self,
        *,
        action: str,
        event_type: str,
        resource_type: str,
        resource_id: str,
        before: Any,
        after: Any,
        meta: dict[str, Any] | None = None,
        reason: str | None = None,
        audit: dict[str, Any] | None = None,
    ) -> None:
        manager = self._audit_log_manager
        if manager is None:
            return

        audit_info = audit or {}
        actor = str(audit_info.get("actor") or "system")
        source = str(audit_info.get("source") or "notification")
        actor_fields = audit_info.get("actor_fields")
        if not isinstance(actor_fields, dict):
            actor_fields = {}
        manager.log_event(
            action=action,
            actor=actor,
            source=source,
            resource_type=resource_type,
            resource_id=str(resource_id),
            event_type=event_type,
            before=before,
            after=after,
            reason=reason,
            request_id=audit_info.get("request_id"),
            client_ip=audit_info.get("client_ip"),
            meta=(meta or {}),
            **actor_fields,
        )

    def _ensure_event_rules_seeded(self) -> None:
        existing_event_types = {
            str(item["event_type"])
            for item in self._store.list_event_rules()
        }
        default_channel_types = self._default_rule_channel_types()
        for event_type in SUPPORTED_EVENT_TYPES:
            if event_type in existing_event_types:
                continue
            self._store.upsert_event_rule(
                event_type=event_type,
                enabled_channel_types=default_channel_types,
            )

    def _default_rule_channel_types(self) -> list[str]:
        enabled_channel_config = self._enabled_channel_config_by_type()
        items = ["in_app"]
        for channel_type_name in ("email", "dingtalk"):
            if enabled_channel_config.get(channel_type_name):
                items.append(channel_type_name)
        return self._normalize_channel_types(items)

    def _enabled_channels_by_type(self) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {channel_type_name: [] for channel_type_name in AVAILABLE_CHANNEL_TYPES}
        for channel in self._store.list_channels(enabled_only=True):
            channel_type_name = str(channel.get("channel_type") or "").strip().lower()
            if channel_type_name in out:
                out[channel_type_name].append(channel)
        return out

    def _enabled_channel_config_by_type(self) -> dict[str, bool]:
        return {
            channel_type_name: bool(items)
            for channel_type_name, items in self._enabled_channels_by_type().items()
        }

    @staticmethod
    def _normalize_channel_types(
        channel_types: list[str] | tuple[str, ...] | set[str] | None,
    ) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in channel_types or []:
            value = str(item or "").strip().lower()
            if not value:
                continue
            if value not in AVAILABLE_CHANNEL_TYPES:
                raise NotificationManagerError("invalid_channel_type", status_code=400)
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized


NotificationService = NotificationManager
NotificationServiceError = NotificationManagerError

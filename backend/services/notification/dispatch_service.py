from __future__ import annotations

import logging
import time
from typing import Any

from .audit import emit_notification_audit
from .event_catalog import SUPPORTED_EVENT_TYPES
from .event_rule_service import NotificationEventRuleService
from .helpers import normalize_channel_types, normalize_recipients, resolve_recipient_address
from .store import NotificationStore

logger = logging.getLogger(__name__)


class NotificationDispatchService:
    def __init__(
        self,
        *,
        store: NotificationStore,
        event_rule_service: NotificationEventRuleService,
        email_adapter: Any,
        dingtalk_adapter: Any,
        audit_log_manager: Any | None = None,
        retry_interval_seconds: int = 60,
    ):
        self._store = store
        self._event_rule_service = event_rule_service
        self._email_adapter = email_adapter
        self._dingtalk_adapter = dingtalk_adapter
        self._audit_log_manager = audit_log_manager
        self._retry_interval_seconds = max(1, int(retry_interval_seconds))

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
        normalized_event_type = str(event_type or "").strip()
        if not normalized_event_type:
            raise ValueError("notification_event_type_required")
        if normalized_event_type not in SUPPORTED_EVENT_TYPES:
            raise ValueError("notification_event_type_unsupported")

        self._event_rule_service.ensure_event_rules_seeded()
        event_rule = self._event_rule_service.get_event_rule(normalized_event_type)
        if event_rule is None:
            raise RuntimeError("notification_event_rule_not_found")

        rule_channel_types = normalize_channel_types(event_rule.get("enabled_channel_types") or [])
        caller_channel_types = normalize_channel_types(channel_types or []) if channel_types is not None else None
        if caller_channel_types is None:
            effective_channel_types = list(rule_channel_types)
        else:
            requested_set = set(caller_channel_types)
            effective_channel_types = [item for item in rule_channel_types if item in requested_set]
        if not effective_channel_types:
            return []

        enabled_channels_by_type = self._event_rule_service.enabled_channels_by_type()
        missing_channel_types = [
            channel_type_name
            for channel_type_name in effective_channel_types
            if not enabled_channels_by_type.get(channel_type_name)
        ]
        if missing_channel_types:
            detail = ",".join(missing_channel_types)
            raise ValueError(f"notification_channel_not_configured:{detail}")

        channels: list[dict[str, Any]] = []
        for channel_type_name in effective_channel_types:
            channels.extend(enabled_channels_by_type.get(channel_type_name) or [])

        normalized_recipients = normalize_recipients(recipients)
        if not normalized_recipients:
            raise ValueError("notification_recipients_required")

        unresolved: list[str] = []
        dispatch_targets: list[tuple[dict[str, Any], dict[str, Any], str]] = []
        for channel in channels:
            for recipient in normalized_recipients:
                address = resolve_recipient_address(channel=channel, recipient=recipient)
                if not address:
                    unresolved.append(
                        f"{channel['channel_id']}:{recipient.get('user_id') or recipient.get('username') or 'unknown'}"
                    )
                    continue
                dispatch_targets.append((channel, recipient, address))

        if unresolved:
            detail = ",".join(unresolved[:10])
            raise ValueError(
                f"notification_recipient_unresolved:{detail}" if detail else "notification_recipient_unresolved"
            )

        jobs: list[dict[str, Any]] = []
        for channel, recipient, address in dispatch_targets:
            existing = None
            if not allow_duplicate:
                existing = self._store.find_duplicate_job(
                    channel_id=str(channel["channel_id"]),
                    event_type=normalized_event_type,
                    recipient_user_id=recipient.get("user_id"),
                    dedupe_key=dedupe_key,
                )
            if existing is not None:
                jobs.append(existing)
                continue

            job = self._store.create_job(
                channel_id=str(channel["channel_id"]),
                event_type=normalized_event_type,
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
            emit_notification_audit(
                self._audit_log_manager,
                action="notification_job_enqueue",
                event_type="create",
                resource_type="notification_job",
                resource_id=str(job["job_id"]),
                before=None,
                after=job,
                meta={
                    "channel_id": channel.get("channel_id"),
                    "channel_type": channel.get("channel_type"),
                    "event_type": normalized_event_type,
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
            raise ValueError("notification_job_not_found")
        channel = self._store.get_channel(str(job["channel_id"]))
        if not channel:
            raise ValueError("notification_channel_not_found")

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
            emit_notification_audit(
                self._audit_log_manager,
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
            emit_notification_audit(
                self._audit_log_manager,
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
            emit_notification_audit(
                self._audit_log_manager,
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
        except Exception as exc:  # noqa: BLE001
            err = str(exc) or exc.__class__.__name__
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
            emit_notification_audit(
                self._audit_log_manager,
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
            except Exception as exc:  # noqa: BLE001
                items.append(
                    {
                        "job_id": int(job["job_id"]),
                        "status": "error",
                        "attempts": int(job.get("attempts") or 0),
                        "last_error": str(exc),
                    }
                )
        return {"total": len(items), "items": items}

    def retry_job(self, *, job_id: int, audit: dict[str, Any] | None = None) -> dict[str, Any]:
        job = self._store.get_job(int(job_id))
        if not job:
            raise ValueError("notification_job_not_found")
        if str(job["status"]) == "sent":
            raise ValueError("notification_job_already_sent")

        self._store.reset_job_for_retry(job_id=int(job_id))
        reset_job = self._store.get_job(int(job_id))
        if not reset_job:
            raise RuntimeError("notification_job_not_found_after_retry_reset")
        self._store.add_delivery_log(
            job_id=int(reset_job["job_id"]),
            channel_id=str(reset_job["channel_id"]),
            status="queued",
            error=None,
        )

        updated = self.dispatch_job(job_id=int(job_id), audit=audit)
        emit_notification_audit(
            self._audit_log_manager,
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
            raise ValueError("notification_job_not_found")
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
        emit_notification_audit(
            self._audit_log_manager,
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
        emit_notification_audit(
            self._audit_log_manager,
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

    def _resolve_adapter(self, channel_type: str):
        kind = str(channel_type or "").strip().lower()
        if kind == "email":
            return self._email_adapter
        if kind == "dingtalk":
            return self._dingtalk_adapter
        raise ValueError("notification_channel_type_unsupported")

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .audit import emit_notification_audit
from .channel_service import NotificationChannelService
from .code_defaults import (
    CODE_OWNED_EVENT_RULES,
    build_code_owned_dingtalk_channel,
)
from .dingtalk_adapter import DingTalkNotificationAdapter
from .dispatch_service import NotificationDispatchService
from .email_adapter import EmailNotificationAdapter
from .event_rule_service import NotificationEventRuleService
from .helpers import (
    normalize_channel_types,
    normalize_recipients,
    normalized_name,
    optional_int_attr,
    resolve_recipient_address,
    string_attr,
)
from .inbox_service import NotificationInboxService
from .recipient_directory_service import NotificationRecipientDirectoryService
from .store import NotificationStore


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

        self._channel_service = NotificationChannelService(
            store=self._store,
            audit_log_manager=self._audit_log_manager,
        )
        self._event_rule_service = NotificationEventRuleService(
            store=self._store,
            audit_log_manager=self._audit_log_manager,
        )
        self._dispatch_service = NotificationDispatchService(
            store=self._store,
            event_rule_service=self._event_rule_service,
            email_adapter=self._email_adapter,
            dingtalk_adapter=self._dingtalk_adapter,
            audit_log_manager=self._audit_log_manager,
            retry_interval_seconds=self._retry_interval_seconds,
        )
        self._inbox_service = NotificationInboxService(
            store=self._store,
            audit_log_manager=self._audit_log_manager,
        )
        self._recipient_directory_service = NotificationRecipientDirectoryService(
            store=self._store,
            dingtalk_adapter=self._dingtalk_adapter,
            audit_log_manager=self._audit_log_manager,
        )
        self._apply_code_owned_defaults()

    def _apply_code_owned_defaults(self) -> None:
        existing_dingtalk = self._store.get_channel("dingtalk-main")
        desired_dingtalk = build_code_owned_dingtalk_channel(existing_dingtalk)
        if self._channel_needs_sync(existing_dingtalk, desired_dingtalk):
            self._store.upsert_channel(
                channel_id=str(desired_dingtalk["channel_id"]),
                channel_type=str(desired_dingtalk["channel_type"]),
                name=str(desired_dingtalk["name"]),
                enabled=bool(desired_dingtalk["enabled"]),
                config=desired_dingtalk.get("config") or {},
            )

        for event_type, enabled_channel_types in CODE_OWNED_EVENT_RULES.items():
            existing_rule = self._store.get_event_rule(event_type)
            normalized_enabled_channel_types = normalize_channel_types(enabled_channel_types)
            existing_types = normalize_channel_types((existing_rule or {}).get("enabled_channel_types") or [])
            if existing_types == normalized_enabled_channel_types:
                continue
            self._store.upsert_event_rule(
                event_type=event_type,
                enabled_channel_types=normalized_enabled_channel_types,
            )

    @staticmethod
    def _channel_needs_sync(current: dict[str, Any] | None, desired: dict[str, Any]) -> bool:
        if not current:
            return True
        if str(current.get("channel_type") or "").strip().lower() != str(desired["channel_type"]).strip().lower():
            return True
        if str(current.get("name") or "").strip() != str(desired["name"]).strip():
            return True
        if bool(current.get("enabled")) != bool(desired["enabled"]):
            return True
        current_config = current.get("config") or {}
        desired_config = desired.get("config") or {}
        return current_config != desired_config

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
        try:
            return self._channel_service.upsert_channel(
                channel_id=channel_id,
                channel_type=channel_type,
                name=name,
                enabled=enabled,
                config=config,
                audit=audit,
            )
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

    def list_channels(self, *, enabled_only: bool = False) -> list[dict[str, Any]]:
        return self._channel_service.list_channels(enabled_only=enabled_only)

    def rebuild_dingtalk_recipient_map_from_org(
        self,
        *,
        channel_id: str,
        user_store: Any,
        org_directory_store: Any,
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            return self._recipient_directory_service.rebuild_dingtalk_recipient_map_from_org(
                channel_id=channel_id,
                user_store=user_store,
                org_directory_store=org_directory_store,
                audit=audit,
            )
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

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
        return self._store.list_delivery_logs(job_id=job_id, limit=limit)

    def list_event_rules(self) -> dict[str, Any]:
        try:
            return self._event_rule_service.list_event_rules()
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

    def upsert_event_rules(
        self,
        *,
        items: list[dict[str, Any]],
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            return self._event_rule_service.upsert_event_rules(items=items, audit=audit)
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

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
        try:
            return self._dispatch_service.notify_event(
                event_type=event_type,
                payload=payload,
                recipients=recipients,
                dedupe_key=dedupe_key,
                allow_duplicate=allow_duplicate,
                max_attempts=max_attempts,
                channel_types=channel_types,
                audit=audit,
            )
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

    def dispatch_job(self, *, job_id: int, audit: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            return self._dispatch_service.dispatch_job(job_id=job_id, audit=audit)
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

    def dispatch_pending(self, *, limit: int = 100, audit: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._dispatch_service.dispatch_pending(limit=limit, audit=audit)

    def retry_job(self, *, job_id: int, audit: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            return self._dispatch_service.retry_job(job_id=job_id, audit=audit)
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

    def resend_job(self, *, job_id: int, audit: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            return self._dispatch_service.resend_job(job_id=job_id, audit=audit)
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

    def list_inbox(
        self,
        *,
        recipient_user_id: str,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> dict[str, Any]:
        try:
            return self._inbox_service.list_inbox(
                recipient_user_id=recipient_user_id,
                limit=limit,
                offset=offset,
                unread_only=unread_only,
            )
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

    def update_inbox_read_state(
        self,
        *,
        job_id: int,
        recipient_user_id: str,
        read: bool,
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            return self._inbox_service.update_inbox_read_state(
                job_id=job_id,
                recipient_user_id=recipient_user_id,
                read=read,
                audit=audit,
            )
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

    def mark_all_inbox_read(
        self,
        *,
        recipient_user_id: str,
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            return self._inbox_service.mark_all_inbox_read(
                recipient_user_id=recipient_user_id,
                audit=audit,
            )
        except (ValueError, RuntimeError) as exc:
            self._raise_manager_error(exc)

    def _raise_manager_error(self, exc: ValueError | RuntimeError) -> None:
        code = str(exc)
        raise NotificationManagerError(code, status_code=self._status_code_for(code, exc)) from exc

    @staticmethod
    def _status_code_for(code: str, exc: ValueError | RuntimeError) -> int:
        explicit = {
            "notification_channel_not_found": 404,
            "notification_job_not_found": 404,
            "notification_message_not_found": 404,
            "notification_message_not_available": 409,
            "notification_event_rule_not_found": 500,
            "notification_org_directory_unavailable": 500,
            "notification_user_store_unavailable": 500,
            "notification_dingtalk_validation_unavailable": 500,
            "notification_job_not_found_after_retry_reset": 500,
            "notification_job_create_failed": 500,
            "notification_channel_upsert_failed": 500,
            "notification_event_rule_upsert_failed": 500,
            "notification_invalid_company_id": 500,
            "notification_invalid_department_id": 500,
        }
        if code in explicit:
            return explicit[code]
        if code.startswith("notification_channel_not_configured:"):
            return 400
        if code.startswith("notification_recipient_unresolved:"):
            return 400
        return 500 if isinstance(exc, RuntimeError) else 400

    @staticmethod
    def _resolve_recipient_address(*, channel: dict[str, Any], recipient: dict[str, str | None]) -> str | None:
        return resolve_recipient_address(channel=channel, recipient=recipient)

    @staticmethod
    def _normalize_recipients(recipients: list[dict[str, Any]] | None) -> list[dict[str, str | None]]:
        return normalize_recipients(recipients)

    @staticmethod
    def _normalize_channel_types(
        channel_types: list[str] | tuple[str, ...] | set[str] | None,
    ) -> list[str]:
        try:
            return normalize_channel_types(channel_types)
        except ValueError as exc:
            raise NotificationManagerError(str(exc), status_code=400) from exc

    @staticmethod
    def _normalized_name(value: Any) -> str:
        return normalized_name(value)

    @staticmethod
    def _string_attr(item: Any, field: str) -> str:
        return string_attr(item, field)

    @staticmethod
    def _optional_int_attr(item: Any, field: str) -> int | None:
        try:
            return optional_int_attr(item, field)
        except RuntimeError as exc:
            raise NotificationManagerError(str(exc), status_code=500) from exc

    @staticmethod
    def _build_dingtalk_recipient_directory(
        org_employees: list[Any],
    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
        return NotificationRecipientDirectoryService.build_dingtalk_recipient_directory(org_employees)

    @staticmethod
    def _list_org_employees_for_recipient_map_rebuild(org_directory_store: Any) -> list[Any]:
        try:
            return NotificationRecipientDirectoryService.list_org_employees_for_recipient_map_rebuild(
                org_directory_store
            )
        except RuntimeError as exc:
            raise NotificationManagerError(str(exc), status_code=500) from exc

    @staticmethod
    def _sync_employee_user_ids_from_org(
        *,
        user_store: Any,
        org_employees: list[Any],
    ) -> dict[str, int]:
        try:
            return NotificationRecipientDirectoryService.sync_employee_user_ids_from_org(
                user_store=user_store,
                org_employees=org_employees,
            )
        except RuntimeError as exc:
            raise NotificationManagerError(str(exc), status_code=500) from exc

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
        emit_notification_audit(
            self._audit_log_manager,
            action=action,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            before=before,
            after=after,
            meta=meta,
            reason=reason,
            audit=audit,
        )


NotificationService = NotificationManager
NotificationServiceError = NotificationManagerError

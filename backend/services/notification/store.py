from __future__ import annotations

from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

from .repositories import (
    NotificationChannelRepository,
    NotificationDeliveryLogRepository,
    NotificationEventRuleRepository,
    NotificationInboxRepository,
    NotificationJobRepository,
)


class NotificationStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.channels = NotificationChannelRepository(self._conn)
        self.event_rules = NotificationEventRuleRepository(self._conn)
        self.jobs = NotificationJobRepository(self._conn)
        self.delivery_logs = NotificationDeliveryLogRepository(self._conn)
        self.inbox = NotificationInboxRepository(self._conn)

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
        return self.channels.upsert_channel(
            channel_id=channel_id,
            channel_type=channel_type,
            name=name,
            enabled=enabled,
            config=config,
        )

    def get_channel(self, channel_id: str) -> dict[str, Any] | None:
        return self.channels.get_channel(channel_id)

    def list_channels(self, *, enabled_only: bool = False) -> list[dict[str, Any]]:
        return self.channels.list_channels(enabled_only=enabled_only)

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
        return self.jobs.create_job(
            channel_id=channel_id,
            event_type=event_type,
            payload=payload,
            recipient_user_id=recipient_user_id,
            recipient_username=recipient_username,
            recipient_address=recipient_address,
            dedupe_key=dedupe_key,
            source_job_id=source_job_id,
            max_attempts=max_attempts,
        )

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        return self.jobs.get_job(job_id)

    def list_jobs(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        event_type: str | None = None,
        channel_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.jobs.list_jobs(limit=limit, status=status, event_type=event_type, channel_type=channel_type)

    def get_event_rule(self, event_type: str) -> dict[str, object] | None:
        return self.event_rules.get_event_rule(event_type)

    def list_event_rules(self) -> list[dict[str, object]]:
        return self.event_rules.list_event_rules()

    def upsert_event_rule(
        self,
        *,
        event_type: str,
        enabled_channel_types: list[str] | tuple[str, ...] | set[str],
    ) -> dict[str, object]:
        return self.event_rules.upsert_event_rule(
            event_type=event_type,
            enabled_channel_types=enabled_channel_types,
        )

    def find_duplicate_job(
        self,
        *,
        channel_id: str,
        event_type: str,
        recipient_user_id: str | None,
        dedupe_key: str | None,
    ) -> dict[str, Any] | None:
        return self.jobs.find_duplicate_job(
            channel_id=channel_id,
            event_type=event_type,
            recipient_user_id=recipient_user_id,
            dedupe_key=dedupe_key,
        )

    def reset_job_for_retry(self, *, job_id: int) -> dict[str, Any]:
        return self.jobs.reset_job_for_retry(job_id=job_id)

    def clone_job_for_resend(self, *, job_id: int, dedupe_key: str) -> dict[str, Any]:
        return self.jobs.clone_job_for_resend(job_id=job_id, dedupe_key=dedupe_key)

    def mark_job_sent(self, *, job_id: int) -> dict[str, Any]:
        return self.jobs.mark_job_sent(job_id=job_id)

    def mark_job_failed(self, *, job_id: int, error: str, retry_interval_seconds: int) -> dict[str, Any]:
        return self.jobs.mark_job_failed(
            job_id=job_id,
            error=error,
            retry_interval_seconds=retry_interval_seconds,
        )

    def list_dispatchable_jobs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.jobs.list_dispatchable_jobs(limit=limit)

    def add_delivery_log(self, *, job_id: int, channel_id: str, status: str, error: str | None = None) -> None:
        self.delivery_logs.add_delivery_log(job_id=job_id, channel_id=channel_id, status=status, error=error)

    def list_delivery_logs(self, *, job_id: int, limit: int = 50) -> list[dict[str, object]]:
        return self.delivery_logs.list_delivery_logs(job_id=job_id, limit=limit)

    def list_inbox(
        self,
        *,
        recipient_user_id: str,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> tuple[int, int, list[dict[str, Any]]]:
        return self.inbox.list_inbox(
            recipient_user_id=recipient_user_id,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        )

    def set_inbox_read_state(
        self,
        *,
        job_id: int,
        recipient_user_id: str,
        read: bool,
    ) -> dict[str, Any] | None:
        updated_job_id = self.inbox.set_inbox_read_state(
            job_id=job_id,
            recipient_user_id=recipient_user_id,
            read=read,
        )
        if updated_job_id is None:
            return None
        return self.get_job(updated_job_id)

    def mark_all_inbox_read(self, *, recipient_user_id: str) -> int:
        return self.inbox.mark_all_inbox_read(recipient_user_id=recipient_user_id)

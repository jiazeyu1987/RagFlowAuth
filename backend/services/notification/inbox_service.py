from __future__ import annotations

from typing import Any

from .audit import emit_notification_audit
from .store import NotificationStore


class NotificationInboxService:
    def __init__(self, *, store: NotificationStore, audit_log_manager: Any | None = None):
        self._store = store
        self._audit_log_manager = audit_log_manager

    def list_inbox(
        self,
        *,
        recipient_user_id: str,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> dict[str, Any]:
        total, unread_count, items = self._store.list_inbox(
            recipient_user_id=recipient_user_id,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        )
        return {"total": total, "unread_count": unread_count, "items": items}

    def update_inbox_read_state(
        self,
        *,
        job_id: int,
        recipient_user_id: str,
        read: bool,
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        before = self._ensure_owned_in_app_job(job_id=job_id, recipient_user_id=recipient_user_id)
        updated = self._store.set_inbox_read_state(
            job_id=int(job_id),
            recipient_user_id=recipient_user_id,
            read=bool(read),
        )
        if not updated:
            raise ValueError("notification_message_not_found")

        self._store.add_delivery_log(
            job_id=int(updated["job_id"]),
            channel_id=str(updated["channel_id"]),
            status=("read" if bool(read) else "unread"),
            error=None,
        )
        emit_notification_audit(
            self._audit_log_manager,
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
        normalized_user_id = str(recipient_user_id or "").strip()
        if not normalized_user_id:
            raise ValueError("recipient_user_id_required")

        unread_ids = self._collect_unread_inbox_job_ids(recipient_user_id=normalized_user_id)
        changed = self._store.mark_all_inbox_read(recipient_user_id=normalized_user_id)

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

        emit_notification_audit(
            self._audit_log_manager,
            action="notification_inbox_mark_all_read",
            event_type="update",
            resource_type="notification_inbox",
            resource_id=normalized_user_id,
            before=None,
            after={"updated_count": int(changed)},
            meta={"updated_count": int(changed)},
            audit=audit,
        )
        return {"updated_count": int(changed)}

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
            raise ValueError("notification_message_not_found")
        channel = self._store.get_channel(str(job["channel_id"]))
        if not channel:
            raise ValueError("notification_channel_not_found")
        if str(channel.get("channel_type") or "").strip().lower() != "in_app":
            raise ValueError("notification_message_not_found")
        if str(job.get("status") or "") != "sent":
            raise ValueError("notification_message_not_available")
        if str(job.get("recipient_user_id") or "").strip() != str(recipient_user_id or "").strip():
            raise ValueError("notification_message_not_found")
        return job

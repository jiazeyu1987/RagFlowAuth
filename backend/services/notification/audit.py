from __future__ import annotations

from typing import Any


def emit_notification_audit(
    audit_log_manager: Any,
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
    if audit_log_manager is None:
        return

    audit_info = audit or {}
    actor = str(audit_info.get("actor") or "system")
    source = str(audit_info.get("source") or "notification")
    actor_fields = audit_info.get("actor_fields")
    if not isinstance(actor_fields, dict):
        actor_fields = {}
    audit_log_manager.log_event(
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

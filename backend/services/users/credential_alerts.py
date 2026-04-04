from __future__ import annotations

from typing import Any


def emit_credential_lock_alert(
    *,
    deps: Any,
    user: Any,
    source: str,
    lock_reason: str,
    lock_until_ms: int | None,
    actor: str | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
) -> None:
    user_id = str(getattr(user, "user_id", "") or "").strip()
    username = str(getattr(user, "username", "") or "").strip()
    if not user_id or not username:
        return

    payload = {
        "user_id": user_id,
        "username": username,
        "source": str(source or "").strip() or "auth",
        "lock_reason": str(lock_reason or "").strip() or "credentials_locked",
        "lock_until_ms": (int(lock_until_ms) if lock_until_ms is not None else None),
    }

    audit = getattr(deps, "audit_log_store", None)
    if audit is not None:
        try:
            audit.log_event(
                action="credential_lockout",
                actor=(str(actor or user_id).strip() or user_id),
                actor_username=username,
                source=str(source or "").strip() or "auth",
                resource_type="user_credentials",
                resource_id=user_id,
                event_type="lock",
                after=payload,
                reason=payload["lock_reason"],
                request_id=request_id,
                client_ip=client_ip,
                meta=payload,
            )
        except Exception:
            pass

    notification_service = getattr(deps, "notification_service", None)
    user_store = getattr(deps, "user_store", None)
    if notification_service is None or user_store is None:
        return

    recipients = []
    seen: set[str] = set()
    for role in ("admin", "sub_admin"):
        try:
            admins = user_store.list_users(role=role, status="active", limit=200)
        except Exception:
            admins = []
        for admin in admins or []:
            admin_user_id = str(getattr(admin, "user_id", "") or "").strip()
            if not admin_user_id or admin_user_id in seen:
                continue
            seen.add(admin_user_id)
            recipients.append(
                {
                    "user_id": admin_user_id,
                    "username": str(getattr(admin, "username", "") or "").strip() or None,
                    "full_name": getattr(admin, "full_name", None),
                    "email": getattr(admin, "email", None),
                }
            )

    if not recipients:
        return

    dedupe_lock_until = payload["lock_until_ms"] if payload["lock_until_ms"] is not None else "none"
    dedupe_key = f"credential_lockout:{user_id}:{source}:{dedupe_lock_until}"
    try:
        jobs = notification_service.notify_event(
            event_type="credential_lockout",
            payload=payload,
            recipients=recipients,
            dedupe_key=dedupe_key,
            audit={"actor": "system", "source": str(source or "").strip() or "auth"},
        )
        for job in jobs:
            notification_service.dispatch_job(
                job_id=int(job["job_id"]),
                audit={"actor": "system", "source": str(source or "").strip() or "auth"},
            )
    except Exception:
        return

from __future__ import annotations

from backend.services.audit_helpers import actor_fields_from_user


def log_password_reset_event(*, deps, request, actor_user, target_user, user_id: str) -> None:
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    client_ip = getattr(getattr(request, "client", None), "host", None)
    deps.audit_log_manager.log_event(
        action="user_password_reset",
        actor=str(getattr(actor_user, "user_id", "") or ""),
        source="users",
        resource_type="user",
        resource_id=str(user_id),
        event_type="update",
        before={"password_changed": False},
        after={"password_changed": True},
        request_id=request_id,
        client_ip=client_ip,
        meta={
            "target_user_id": user_id,
            "target_username": getattr(target_user, "username", None),
        },
        **actor_fields_from_user(deps, actor_user),
    )

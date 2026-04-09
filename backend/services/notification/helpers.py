from __future__ import annotations

from typing import Any

from .event_catalog import AVAILABLE_CHANNEL_TYPES


def normalize_channel_types(channel_types: list[str] | tuple[str, ...] | set[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in channel_types or []:
        value = str(item or "").strip().lower()
        if not value:
            continue
        if value not in AVAILABLE_CHANNEL_TYPES:
            raise ValueError("invalid_channel_type")
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def normalize_recipients(recipients: list[dict[str, Any]] | None) -> list[dict[str, str | None]]:
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


def resolve_recipient_address(*, channel: dict[str, Any], recipient: dict[str, str | None]) -> str | None:
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
        if employee_user_id:
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


def normalized_name(value: Any) -> str:
    return str(value or "").strip()


def string_attr(item: Any, field: str) -> str:
    value = getattr(item, field, None)
    if value is None and isinstance(item, dict):
        value = item.get(field)
    return str(value or "").strip()


def optional_int_attr(item: Any, field: str) -> int | None:
    value = getattr(item, field, None)
    if value is None and isinstance(item, dict):
        value = item.get(field)
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(value)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"notification_invalid_{field}") from exc

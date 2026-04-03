from __future__ import annotations

import time
from typing import Any


def is_login_disabled_now(user: Any, *, now_ms: int | None = None) -> bool:
    disabled, _ = resolve_login_block(user, now_ms=now_ms)
    return disabled


def resolve_login_block(user: Any, *, now_ms: int | None = None) -> tuple[bool, str | None]:
    now = int(now_ms) if now_ms is not None else int(time.time() * 1000)

    status = str(getattr(user, "status", "") or "").strip().lower()
    if status and status != "active":
        return True, "account_inactive"

    raw_credential_locked_until = getattr(user, "credential_locked_until_ms", None)
    if raw_credential_locked_until is not None:
        try:
            credential_locked_until_ms = int(raw_credential_locked_until)
        except Exception:
            credential_locked_until_ms = None
        if credential_locked_until_ms is not None and now < credential_locked_until_ms:
            return True, "credentials_locked"

    disable_enabled = bool(getattr(user, "disable_login_enabled", False))
    if not disable_enabled:
        return False, None

    raw_until = getattr(user, "disable_login_until_ms", None)
    if raw_until is None:
        return True, "account_disabled"
    try:
        until_ms = int(raw_until)
    except Exception:
        return True, "account_disabled"

    if now < until_ms:
        return True, "account_disabled"
    return False, None

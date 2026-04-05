from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tool.maintenance.core.ragflow_base_url_guard import (
    BaseUrlFixResult,
    DEFAULT_REMOTE_APP_DIR,
    desired_base_url_for_role,
    ensure_remote_base_url,
    read_remote_base_url,
)


LogFn = Callable[[str], None]


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    error: str = ""


def ensure_remote_role_base_url(
    *,
    role: str,
    server_ip: str,
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
    log: LogFn | None = None,
) -> BaseUrlFixResult:
    """
    Ensure the remote server ragflow_config.json base_url points to the correct environment.

    Roles: local/test/prod (local uses local file elsewhere; this function is for remote only).
    """
    desired = desired_base_url_for_role(role)
    return ensure_remote_base_url(server_ip=server_ip, desired=desired, app_dir=app_dir, log=log, role_name=role.upper())


def read_remote_base_url_safe(
    *,
    server_ip: str,
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
) -> tuple[bool, str]:
    return read_remote_base_url(server_ip=server_ip, app_dir=app_dir, timeout_seconds=60)


def require_base_url_contains(
    *,
    base_url: str,
    expected_substring: str,
    log: LogFn | None = None,
    context: str = "",
) -> PreflightResult:
    if expected_substring and expected_substring in (base_url or ""):
        return PreflightResult(ok=True)
    if log:
        prefix = f"[{context}] " if context else ""
        log(f"{prefix}[ERROR] base_url mismatch: got={base_url!r} expected_contains={expected_substring!r}")
    return PreflightResult(ok=False, error="base_url mismatch")


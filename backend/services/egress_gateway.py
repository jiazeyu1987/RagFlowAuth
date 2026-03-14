from __future__ import annotations

import threading
import urllib.error
import urllib.request
from typing import Any

import requests

from backend.services.egress_mode_runtime import EgressModeRuntime

_GATEWAY_LOCK = threading.Lock()
_GATEWAY_INSTALLED = False

_ORIGINAL_URLLIB_URLOPEN = urllib.request.urlopen
_ORIGINAL_REQUESTS_SESSION_REQUEST = requests.sessions.Session.request


def _runtime_guard() -> EgressModeRuntime:
    # Resolve policy store path lazily so test/runtime DATABASE_PATH overrides can take effect.
    return EgressModeRuntime()


def _extract_urllib_target(url: Any) -> str:
    if isinstance(url, urllib.request.Request):
        return str(url.full_url or url.get_full_url() or "")
    return str(url or "")


def _check_egress_or_raise(*, target: str, source: str, error_type: str) -> None:
    decision = _runtime_guard().evaluate_target(target, source=source)
    if decision.allowed:
        return
    reason = str(decision.reason or "egress_blocked_by_mode")
    if error_type == "urllib":
        raise urllib.error.URLError(reason)
    raise requests.exceptions.RequestException(reason)


def install_egress_gateway() -> None:
    global _GATEWAY_INSTALLED
    with _GATEWAY_LOCK:
        if _GATEWAY_INSTALLED:
            return

        def _guarded_urlopen(url, *args, **kwargs):
            target = _extract_urllib_target(url)
            _check_egress_or_raise(
                target=target,
                source="egress_gateway:urllib",
                error_type="urllib",
            )
            return _ORIGINAL_URLLIB_URLOPEN(url, *args, **kwargs)

        def _guarded_request(session, method, url, *args, **kwargs):
            _check_egress_or_raise(
                target=str(url or ""),
                source=f"egress_gateway:requests:{str(method or '').lower()}",
                error_type="requests",
            )
            return _ORIGINAL_REQUESTS_SESSION_REQUEST(session, method, url, *args, **kwargs)

        urllib.request.urlopen = _guarded_urlopen  # type: ignore[assignment]
        requests.sessions.Session.request = _guarded_request  # type: ignore[assignment]
        _GATEWAY_INSTALLED = True


def uninstall_egress_gateway() -> None:
    global _GATEWAY_INSTALLED
    with _GATEWAY_LOCK:
        if not _GATEWAY_INSTALLED:
            return
        urllib.request.urlopen = _ORIGINAL_URLLIB_URLOPEN  # type: ignore[assignment]
        requests.sessions.Session.request = _ORIGINAL_REQUESTS_SESSION_REQUEST  # type: ignore[assignment]
        _GATEWAY_INSTALLED = False


def is_egress_gateway_installed() -> bool:
    with _GATEWAY_LOCK:
        return bool(_GATEWAY_INSTALLED)

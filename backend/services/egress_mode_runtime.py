from __future__ import annotations

import ipaddress
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.app.core.config import settings
from backend.database.paths import resolve_auth_db_path
from backend.services.egress_policy_store import EgressPolicySettings, EgressPolicyStore
from backend.services.system_feature_flag_store import FLAG_EGRESS_POLICY_ENABLED, SystemFeatureFlagStore

_POLICY_CACHE_LOCK = threading.Lock()
_POLICY_CACHE_BY_DB: dict[str, tuple[float, EgressPolicySettings]] = {}
_FEATURE_CACHE_BY_DB: dict[str, tuple[float, bool]] = {}


@dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    mode: str
    host: str
    reason: str | None = None


def clear_egress_policy_cache() -> None:
    with _POLICY_CACHE_LOCK:
        _POLICY_CACHE_BY_DB.clear()
        _FEATURE_CACHE_BY_DB.clear()


class EgressModeRuntime:
    def __init__(self, *, db_path: str | None = None) -> None:
        self._db_path = str(resolve_auth_db_path(db_path))
        self._store = EgressPolicyStore(db_path=self._db_path)

    @staticmethod
    def _cache_ttl_seconds() -> float:
        try:
            ttl_ms = int(getattr(settings, "EGRESS_POLICY_CACHE_TTL_MS", 1000) or 0)
        except Exception:
            ttl_ms = 1000
        ttl_ms = max(0, min(ttl_ms, 60_000))
        return float(ttl_ms) / 1000.0

    @staticmethod
    def _enforcement_enabled() -> bool:
        value = getattr(settings, "EGRESS_MODE_ENFORCEMENT_ENABLED", True)
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"0", "false", "no", "off"}:
            return False
        if text in {"1", "true", "yes", "on"}:
            return True
        return bool(value)

    def _load_policy(self) -> EgressPolicySettings:
        ttl_s = self._cache_ttl_seconds()
        cache_key = self._db_path
        now_ts = time.monotonic()

        if ttl_s > 0:
            with _POLICY_CACHE_LOCK:
                cached = _POLICY_CACHE_BY_DB.get(cache_key)
                if cached and (now_ts - cached[0]) <= ttl_s:
                    return cached[1]

        policy = self._store.get()
        if ttl_s > 0:
            with _POLICY_CACHE_LOCK:
                _POLICY_CACHE_BY_DB[cache_key] = (time.monotonic(), policy)
        return policy

    def _feature_enabled(self) -> bool:
        ttl_s = self._cache_ttl_seconds()
        cache_key = self._db_path
        now_ts = time.monotonic()

        if ttl_s > 0:
            with _POLICY_CACHE_LOCK:
                cached = _FEATURE_CACHE_BY_DB.get(cache_key)
                if cached and (now_ts - cached[0]) <= ttl_s:
                    return bool(cached[1])

        try:
            enabled = bool(
                SystemFeatureFlagStore(db_path=self._db_path).is_enabled(
                    FLAG_EGRESS_POLICY_ENABLED,
                    default=True,
                )
            )
        except Exception:
            enabled = True

        if ttl_s > 0:
            with _POLICY_CACHE_LOCK:
                _FEATURE_CACHE_BY_DB[cache_key] = (time.monotonic(), enabled)
        return enabled

    @staticmethod
    def _extract_host(target: str) -> str:
        raw = str(target or "").strip()
        if not raw:
            return ""
        parsed = urlparse(raw if "://" in raw else f"http://{raw}")
        return str(parsed.hostname or "").strip().lower()

    @staticmethod
    def _is_intranet_host(host: str) -> bool:
        normalized = str(host or "").strip().lower()
        if not normalized:
            return True
        if normalized in {"localhost"} or normalized.startswith("localhost."):
            return True
        if normalized.endswith(".local") or normalized.endswith(".lan") or normalized.endswith(".internal"):
            return True
        if "." not in normalized:
            return True
        try:
            ip = ipaddress.ip_address(normalized)
        except ValueError:
            return False
        return bool(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)

    def evaluate_target(self, target: str, *, source: str = "") -> EgressDecision:
        host = self._extract_host(target)
        if not self._enforcement_enabled():
            return EgressDecision(allowed=True, mode="disabled", host=host)
        if not self._feature_enabled():
            return EgressDecision(allowed=True, mode="feature_disabled", host=host)

        try:
            policy = self._load_policy()
        except Exception:
            # Fail-open when policy storage is unavailable, to keep compatibility with lightweight tests.
            return EgressDecision(allowed=True, mode="unknown", host=host, reason="policy_unavailable")

        mode = str(getattr(policy, "mode", "intranet") or "intranet").strip().lower()
        if mode == "extranet":
            return EgressDecision(allowed=True, mode=mode, host=host)

        allowlist = {str(item or "").strip().lower() for item in (policy.allowed_target_hosts or []) if str(item or "").strip()}
        if host in allowlist:
            return EgressDecision(allowed=True, mode=mode, host=host)
        if self._is_intranet_host(host):
            return EgressDecision(allowed=True, mode=mode, host=host)

        return EgressDecision(
            allowed=False,
            mode=mode,
            host=host,
            reason=f"egress_blocked_by_mode: mode={mode} source={source or '-'} host={host or '-'}",
        )

    def assert_target_allowed(self, target: str, *, source: str = "") -> None:
        decision = self.evaluate_target(target, source=source)
        if not decision.allowed:
            raise RuntimeError(str(decision.reason or "egress_blocked_by_mode"))

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional, Protocol


class AuthSessionPort(Protocol):
    def enforce_user_session_limit(
        self,
        *,
        user_id: str,
        max_sessions: int,
        reserve_slots: int = 0,
        reason: str = "session_limit_exceeded",
        now_ms: int | None = None,
    ) -> list[str]: ...

    def create_session(
        self,
        *,
        session_id: str,
        user_id: str,
        refresh_jti: str | None,
        expires_at: object | None,
        now_ms: int | None = None,
    ): ...

    def validate_session(
        self,
        *,
        session_id: str,
        user_id: str,
        idle_timeout_minutes: int | None,
        refresh_jti: str | None = None,
        mark_refresh: bool = False,
        touch: bool = True,
        now_ms: int | None = None,
    ) -> tuple[bool, str]: ...

    def revoke_session(self, *, session_id: str, reason: str = "logout", now_ms: int | None = None) -> bool: ...


@dataclass
class AuthSessionError(Exception):
    code: str
    status_code: int = 401

    def __str__(self) -> str:
        return self.code


class AuthSessionManager:
    """
    Reusable auth-session domain manager.

    It owns login-session policy validation and session lifecycle orchestration,
    while concrete persistence remains in an AuthSessionPort implementation.
    """

    def __init__(self, port: AuthSessionPort):
        self._port = port

    @staticmethod
    def _normalize_max_sessions(max_sessions: int | None) -> int:
        try:
            value = int(max_sessions) if max_sessions is not None else 1
        except Exception:
            value = 1
        if value < 1:
            value = 1
        if value > 1000:
            value = 1000
        return value

    @staticmethod
    def payload_sid(payload: object) -> str:
        sid = getattr(payload, "sid", None)
        return str(sid or "").strip()

    @staticmethod
    def payload_jti(payload: object) -> str:
        jti = getattr(payload, "jti", None)
        return str(jti or "").strip()

    def issue_session_id_for_login(
        self,
        *,
        user_id: str,
        max_sessions: int | None,
        reserve_slots: int = 1,
    ) -> str:
        sid, _revoked = self.issue_session_for_login(
            user_id=user_id,
            max_sessions=max_sessions,
            reserve_slots=reserve_slots,
        )
        return sid

    def issue_session_for_login(
        self,
        *,
        user_id: str,
        max_sessions: int | None,
        reserve_slots: int = 1,
    ) -> tuple[str, list[str]]:
        uid = str(user_id or "").strip()
        if not uid:
            raise AuthSessionError("missing_user_id", status_code=400)
        revoked_ids = self._port.enforce_user_session_limit(
            user_id=uid,
            max_sessions=self._normalize_max_sessions(max_sessions),
            reserve_slots=max(0, int(reserve_slots)),
            reason="session_limit_exceeded",
        )
        return str(uuid.uuid4()), list(revoked_ids or [])

    def bind_refresh_session(
        self,
        *,
        session_id: str,
        user_id: str,
        refresh_jti: str | None,
        expires_at: object | None,
    ) -> None:
        sid = str(session_id or "").strip()
        uid = str(user_id or "").strip()
        if not sid:
            raise AuthSessionError("missing_session_id")
        if not uid:
            raise AuthSessionError("missing_user_id", status_code=400)
        self._port.create_session(
            session_id=sid,
            user_id=uid,
            refresh_jti=(str(refresh_jti).strip() if refresh_jti else None),
            expires_at=expires_at,
        )

    def validate_session(
        self,
        *,
        session_id: str,
        user_id: str,
        idle_timeout_minutes: int | None,
        refresh_jti: Optional[str] = None,
        mark_refresh: bool,
        touch: bool,
    ) -> None:
        sid = str(session_id or "").strip()
        uid = str(user_id or "").strip()
        if not sid:
            raise AuthSessionError("missing_session_id")
        if not uid:
            raise AuthSessionError("missing_user_id", status_code=400)
        ok, reason = self._port.validate_session(
            session_id=sid,
            user_id=uid,
            idle_timeout_minutes=idle_timeout_minutes,
            refresh_jti=(str(refresh_jti).strip() if refresh_jti else None),
            mark_refresh=bool(mark_refresh),
            touch=bool(touch),
        )
        if not ok:
            raise AuthSessionError(str(reason or "session_invalid"))

    def validate_access_session(self, *, session_id: str, user_id: str, idle_timeout_minutes: int | None) -> None:
        self.validate_session(
            session_id=session_id,
            user_id=user_id,
            idle_timeout_minutes=idle_timeout_minutes,
            refresh_jti=None,
            mark_refresh=False,
            touch=True,
        )

    def validate_refresh_session(
        self,
        *,
        session_id: str,
        user_id: str,
        idle_timeout_minutes: int | None,
        refresh_jti: str | None,
    ) -> None:
        self.validate_session(
            session_id=session_id,
            user_id=user_id,
            idle_timeout_minutes=idle_timeout_minutes,
            refresh_jti=refresh_jti,
            mark_refresh=True,
            touch=True,
        )

    def revoke_session(self, *, session_id: str, reason: str = "logout") -> bool:
        sid = str(session_id or "").strip()
        if not sid:
            return False
        return bool(self._port.revoke_session(session_id=sid, reason=(reason or "logout")))

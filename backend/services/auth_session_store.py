from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass
class AuthLoginSession:
    session_id: str
    user_id: str
    refresh_jti: Optional[str]
    created_at_ms: int
    last_activity_at_ms: int
    last_refresh_at_ms: Optional[int]
    expires_at_ms: Optional[int]
    revoked_at_ms: Optional[int]
    revoked_reason: Optional[str]

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at_ms is not None


class AuthSessionStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _to_ms(value: object | None) -> int | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return int(value.timestamp() * 1000)
        if isinstance(value, (int, float)):
            # JWT exp from some decoders may already be seconds.
            num = float(value)
            if num > 10_000_000_000:
                return int(num)
            return int(num * 1000)
        return None

    @staticmethod
    def _from_row(row) -> AuthLoginSession:
        return AuthLoginSession(
            session_id=str(row["session_id"]),
            user_id=str(row["user_id"]),
            refresh_jti=(str(row["refresh_jti"]) if row["refresh_jti"] is not None else None),
            created_at_ms=int(row["created_at_ms"] or 0),
            last_activity_at_ms=int(row["last_activity_at_ms"] or 0),
            last_refresh_at_ms=(int(row["last_refresh_at_ms"]) if row["last_refresh_at_ms"] is not None else None),
            expires_at_ms=(int(row["expires_at_ms"]) if row["expires_at_ms"] is not None else None),
            revoked_at_ms=(int(row["revoked_at_ms"]) if row["revoked_at_ms"] is not None else None),
            revoked_reason=(str(row["revoked_reason"]) if row["revoked_reason"] is not None else None),
        )

    def create_session(
        self,
        *,
        session_id: str,
        user_id: str,
        refresh_jti: str | None,
        expires_at: object | None,
        now_ms: int | None = None,
    ) -> AuthLoginSession:
        now = self._now_ms() if now_ms is None else int(now_ms)
        expires_at_ms = self._to_ms(expires_at)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO auth_login_sessions (
                    session_id, user_id, refresh_jti,
                    created_at_ms, last_activity_at_ms, last_refresh_at_ms,
                    expires_at_ms, revoked_at_ms, revoked_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    str(session_id),
                    str(user_id),
                    str(refresh_jti) if refresh_jti else None,
                    now,
                    now,
                    now,
                    expires_at_ms,
                ),
            )
            conn.commit()
        created = self.get_session(session_id)
        if not created:
            raise ValueError("auth_session_create_failed")
        return created

    def get_session(self, session_id: str) -> AuthLoginSession | None:
        sid = str(session_id or "").strip()
        if not sid:
            return None
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT session_id, user_id, refresh_jti, created_at_ms,
                       last_activity_at_ms, last_refresh_at_ms, expires_at_ms,
                       revoked_at_ms, revoked_reason
                FROM auth_login_sessions
                WHERE session_id = ?
                """,
                (sid,),
            ).fetchone()
            return self._from_row(row) if row else None

    def list_active_sessions(self, *, user_id: str, now_ms: int | None = None) -> list[AuthLoginSession]:
        uid = str(user_id or "").strip()
        if not uid:
            return []
        now = self._now_ms() if now_ms is None else int(now_ms)
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT session_id, user_id, refresh_jti, created_at_ms,
                       last_activity_at_ms, last_refresh_at_ms, expires_at_ms,
                       revoked_at_ms, revoked_reason
                FROM auth_login_sessions
                WHERE user_id = ?
                  AND revoked_at_ms IS NULL
                  AND (expires_at_ms IS NULL OR expires_at_ms > ?)
                ORDER BY COALESCE(last_activity_at_ms, created_at_ms) DESC, created_at_ms DESC
                """,
                (uid, now),
            ).fetchall()
            return [self._from_row(row) for row in rows]

    def get_active_session_summaries(
        self,
        *,
        idle_timeout_by_user: dict[str, int | None],
        now_ms: int | None = None,
    ) -> dict[str, dict[str, int | None]]:
        if not idle_timeout_by_user:
            return {}

        normalized: dict[str, int] = {}
        for user_id, idle_minutes in idle_timeout_by_user.items():
            uid = str(user_id or "").strip()
            if not uid:
                continue
            try:
                idle = int(idle_minutes) if idle_minutes is not None else 120
            except Exception:
                idle = 120
            if idle < 1:
                idle = 1
            normalized[uid] = idle

        if not normalized:
            return {}

        now = self._now_ms() if now_ms is None else int(now_ms)
        result: dict[str, dict[str, int | None]] = {
            uid: {
                "active_session_count": 0,
                "active_session_last_activity_at_ms": None,
            }
            for uid in normalized.keys()
        }

        user_ids = list(normalized.keys())
        placeholders = ",".join("?" for _ in user_ids)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT user_id, created_at_ms, last_activity_at_ms
                FROM auth_login_sessions
                WHERE user_id IN ({placeholders})
                  AND revoked_at_ms IS NULL
                  AND (expires_at_ms IS NULL OR expires_at_ms > ?)
                """,
                [*user_ids, now],
            ).fetchall()

        for row in rows:
            uid = str(row["user_id"] or "").strip()
            if uid not in normalized:
                continue

            created_raw = row["created_at_ms"]
            created_at = int(created_raw) if created_raw is not None else 0
            last_activity_raw = row["last_activity_at_ms"]
            if last_activity_raw is not None:
                last_activity = int(last_activity_raw)
            elif created_raw is not None:
                last_activity = int(created_raw)
            else:
                last_activity = now
            idle_minutes = normalized[uid]
            if (now - last_activity) > idle_minutes * 60 * 1000:
                continue

            entry = result[uid]
            entry["active_session_count"] = int(entry["active_session_count"] or 0) + 1
            prev_last = entry["active_session_last_activity_at_ms"]
            if prev_last is None or last_activity > int(prev_last):
                entry["active_session_last_activity_at_ms"] = last_activity

        return result

    def get_active_session_summary(
        self,
        *,
        user_id: str,
        idle_timeout_minutes: int | None,
        now_ms: int | None = None,
    ) -> dict[str, int | None]:
        uid = str(user_id or "").strip()
        if not uid:
            return {
                "active_session_count": 0,
                "active_session_last_activity_at_ms": None,
            }
        summaries = self.get_active_session_summaries(
            idle_timeout_by_user={uid: idle_timeout_minutes},
            now_ms=now_ms,
        )
        return summaries.get(
            uid,
            {
                "active_session_count": 0,
                "active_session_last_activity_at_ms": None,
            },
        )

    def enforce_user_session_limit(
        self,
        *,
        user_id: str,
        max_sessions: int,
        reserve_slots: int = 0,
        reason: str = "session_limit_exceeded",
        now_ms: int | None = None,
    ) -> list[str]:
        uid = str(user_id or "").strip()
        if not uid:
            return []
        try:
            max_count = int(max_sessions)
        except Exception:
            max_count = 1
        if max_count < 1:
            max_count = 1
        keep_count = max(max_count - max(0, int(reserve_slots)), 0)
        now = self._now_ms() if now_ms is None else int(now_ms)
        active = self.list_active_sessions(user_id=uid, now_ms=now)
        if len(active) <= keep_count:
            return []
        to_revoke = active[keep_count:]
        ids = [s.session_id for s in to_revoke if s.session_id]
        if not ids:
            return []
        with self._conn() as conn:
            placeholders = ",".join("?" for _ in ids)
            conn.execute(
                f"""
                UPDATE auth_login_sessions
                SET revoked_at_ms = ?, revoked_reason = ?
                WHERE session_id IN ({placeholders})
                """,
                [now, str(reason or "session_limit_exceeded"), *ids],
            )
            conn.commit()
        return ids

    def revoke_session(self, *, session_id: str, reason: str = "logout", now_ms: int | None = None) -> bool:
        sid = str(session_id or "").strip()
        if not sid:
            return False
        now = self._now_ms() if now_ms is None else int(now_ms)
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE auth_login_sessions
                SET revoked_at_ms = ?, revoked_reason = ?
                WHERE session_id = ? AND revoked_at_ms IS NULL
                """,
                (now, str(reason or "logout"), sid),
            )
            conn.commit()
            return bool(cur.rowcount)

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
    ) -> tuple[bool, str]:
        sid = str(session_id or "").strip()
        uid = str(user_id or "").strip()
        if not sid:
            return False, "missing_session_id"
        if not uid:
            return False, "missing_user_id"

        now = self._now_ms() if now_ms is None else int(now_ms)

        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT session_id, user_id, refresh_jti, created_at_ms,
                       last_activity_at_ms, last_refresh_at_ms, expires_at_ms,
                       revoked_at_ms, revoked_reason
                FROM auth_login_sessions
                WHERE session_id = ? AND user_id = ?
                """,
                (sid, uid),
            ).fetchone()
            if not row:
                return False, "session_not_found"

            session = self._from_row(row)
            if session.revoked_at_ms is not None:
                return False, "session_revoked"

            if session.expires_at_ms is not None and session.expires_at_ms <= now:
                conn.execute(
                    """
                    UPDATE auth_login_sessions
                    SET revoked_at_ms = ?, revoked_reason = ?
                    WHERE session_id = ? AND revoked_at_ms IS NULL
                    """,
                    (now, "refresh_expired", sid),
                )
                conn.commit()
                return False, "refresh_expired"

            if refresh_jti is not None and session.refresh_jti and str(session.refresh_jti) != str(refresh_jti):
                return False, "refresh_jti_mismatch"

            try:
                idle_minutes = int(idle_timeout_minutes) if idle_timeout_minutes is not None else 120
            except Exception:
                idle_minutes = 120
            if idle_minutes < 1:
                idle_minutes = 1

            if session.last_activity_at_ms is not None:
                last_activity = int(session.last_activity_at_ms)
            elif session.created_at_ms is not None:
                last_activity = int(session.created_at_ms)
            else:
                last_activity = now
            if (now - last_activity) > idle_minutes * 60 * 1000:
                conn.execute(
                    """
                    UPDATE auth_login_sessions
                    SET revoked_at_ms = ?, revoked_reason = ?
                    WHERE session_id = ? AND revoked_at_ms IS NULL
                    """,
                    (now, "idle_timeout", sid),
                )
                conn.commit()
                return False, "idle_timeout"

            if touch:
                if mark_refresh:
                    conn.execute(
                        """
                        UPDATE auth_login_sessions
                        SET last_activity_at_ms = ?, last_refresh_at_ms = ?
                        WHERE session_id = ? AND revoked_at_ms IS NULL
                        """,
                        (now, now, sid),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE auth_login_sessions
                        SET last_activity_at_ms = ?
                        WHERE session_id = ? AND revoked_at_ms IS NULL
                        """,
                        (now, sid),
                    )
                conn.commit()

        return True, "ok"

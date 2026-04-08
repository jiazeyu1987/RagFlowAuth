from __future__ import annotations

import time
from typing import Callable

from .password import hash_password, verify_password


DEFAULT_CREDENTIAL_FAILURE_LIMIT = 5
DEFAULT_CREDENTIAL_FAILURE_WINDOW_MS = 15 * 60 * 1000
DEFAULT_CREDENTIAL_LOCKOUT_MS = 15 * 60 * 1000


class UserCredentialStore:
    def __init__(
        self,
        *,
        connection_factory: Callable[[], object],
        now_ms_factory: Callable[[], int] | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._now_ms_factory = now_ms_factory or (lambda: int(time.time() * 1000))

    def update_password(self, user_id: str, new_password: str) -> None:
        self.update_password_hash(user_id, hash_password(new_password))

    def update_password_hash(self, user_id: str, password_hash_value: str) -> None:
        now_ms = self._now_ms_factory()
        conn = self._connection_factory()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT password_hash FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row[0]:
                cursor.execute(
                    """
                    INSERT INTO password_history (user_id, password_hash, created_at_ms)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, str(row[0]), now_ms),
                )
            cursor.execute(
                """
                UPDATE users
                SET password_hash = ?,
                    password_changed_at_ms = ?,
                    credential_fail_count = 0,
                    credential_fail_window_started_at_ms = NULL,
                    credential_locked_until_ms = NULL
                WHERE user_id = ?
                """,
                (password_hash_value, now_ms, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def clear_credential_failures(self, user_id: str) -> None:
        conn = self._connection_factory()
        try:
            conn.execute(
                """
                UPDATE users
                SET credential_fail_count = 0,
                    credential_fail_window_started_at_ms = NULL,
                    credential_locked_until_ms = NULL
                WHERE user_id = ?
                """,
                (user_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def record_credential_failure(
        self,
        user_id: str,
        *,
        now_ms: int | None = None,
        max_failures: int = DEFAULT_CREDENTIAL_FAILURE_LIMIT,
        window_ms: int = DEFAULT_CREDENTIAL_FAILURE_WINDOW_MS,
        lockout_ms: int = DEFAULT_CREDENTIAL_LOCKOUT_MS,
    ) -> tuple[int | None, bool]:
        current_ms = self._now_ms_factory() if now_ms is None else int(now_ms)
        conn = self._connection_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT credential_fail_count, credential_fail_window_started_at_ms, credential_locked_until_ms
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if row is None:
                conn.commit()
                return None, False

            previous_count = int(row[0] or 0)
            previous_window_start = int(row[1]) if row[1] is not None else None
            previous_locked_until = int(row[2]) if row[2] is not None else None

            if previous_locked_until is not None and current_ms < previous_locked_until:
                conn.commit()
                return previous_locked_until, False

            if previous_window_start is None or current_ms - previous_window_start > int(window_ms):
                next_count = 1
                next_window_start = current_ms
            else:
                next_count = previous_count + 1
                next_window_start = previous_window_start

            next_locked_until = None
            newly_locked = False
            if next_count >= int(max_failures):
                next_locked_until = current_ms + int(lockout_ms)
                newly_locked = True

            conn.execute(
                """
                UPDATE users
                SET credential_fail_count = ?,
                    credential_fail_window_started_at_ms = ?,
                    credential_locked_until_ms = ?
                WHERE user_id = ?
                """,
                (next_count, next_window_start, next_locked_until, user_id),
            )
            conn.commit()
            return next_locked_until, newly_locked
        finally:
            conn.close()

    def password_matches_recent_history(
        self,
        *,
        user_id: str,
        password: str,
        current_password_hash: str | None,
        limit: int = 5,
    ) -> bool:
        ok, _ = verify_password(password, current_password_hash)
        if ok:
            return True

        conn = self._connection_factory()
        try:
            rows = conn.execute(
                """
                SELECT password_hash
                FROM password_history
                WHERE user_id = ?
                ORDER BY created_at_ms DESC, id DESC
                LIMIT ?
                """,
                (user_id, int(max(1, limit))),
            ).fetchall()
        finally:
            conn.close()

        for row in rows:
            stored_hash = str(row[0] or "")
            matched, _ = verify_password(password, stored_hash)
            if matched:
                return True
        return False

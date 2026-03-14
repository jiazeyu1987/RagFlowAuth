from __future__ import annotations

import hashlib
import time
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

# Built-in super admin credentials (hardcoded as requested).
SUPER_ADMIN_USERNAME = "SuperAdmin"
SUPER_ADMIN_PASSWORD = "SuperAdmin"
SUPER_ADMIN_EMAIL = "superadmin@local"
SUPER_ADMIN_USER_ID = "builtin_super_admin"
SUPER_ADMIN_CREATED_BY = "system_super_admin"


def _hash_password(password: str) -> str:
    return hashlib.sha256(str(password or "").encode("utf-8")).hexdigest()


def normalize_username(value: str | None) -> str:
    return str(value or "").strip().lower()


def is_super_admin_username(value: str | None) -> bool:
    return normalize_username(value) == normalize_username(SUPER_ADMIN_USERNAME)


def is_super_admin_user(user: Any) -> bool:
    if user is None:
        return False
    username = getattr(user, "username", None)
    user_id = str(getattr(user, "user_id", "") or "").strip()
    if is_super_admin_username(username):
        return True
    return user_id == SUPER_ADMIN_USER_ID


def ensure_builtin_super_admin(*, db_path: str | None = None) -> None:
    path = resolve_auth_db_path(db_path)
    conn = connect_sqlite(path)
    try:
        cursor = conn.cursor()
        now_ms = int(time.time() * 1000)

        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE lower(trim(username)) = ?
            LIMIT 1
            """,
            (normalize_username(SUPER_ADMIN_USERNAME),),
        )
        row = cursor.fetchone()
        if row:
            user_id = str(row["user_id"] if isinstance(row, dict) else row[0])
            cursor.execute(
                """
                UPDATE users
                SET username = ?,
                    password_hash = ?,
                    email = ?,
                    role = 'admin',
                    status = 'active',
                    max_login_sessions = 10,
                    idle_timeout_minutes = 240
                WHERE user_id = ?
                """,
                (
                    SUPER_ADMIN_USERNAME,
                    _hash_password(SUPER_ADMIN_PASSWORD),
                    SUPER_ADMIN_EMAIL,
                    user_id,
                ),
            )
        else:
            user_id = SUPER_ADMIN_USER_ID
            cursor.execute(
                """
                INSERT INTO users (
                    user_id,
                    username,
                    password_hash,
                    email,
                    role,
                    group_id,
                    status,
                    max_login_sessions,
                    idle_timeout_minutes,
                    created_at_ms,
                    last_login_at_ms,
                    created_by
                ) VALUES (?, ?, ?, ?, 'admin', NULL, 'active', 10, 240, ?, NULL, ?)
                """,
                (
                    user_id,
                    SUPER_ADMIN_USERNAME,
                    _hash_password(SUPER_ADMIN_PASSWORD),
                    SUPER_ADMIN_EMAIL,
                    now_ms,
                    SUPER_ADMIN_CREATED_BY,
                ),
            )

        cursor.execute("SELECT group_id FROM permission_groups WHERE group_name = 'admin' LIMIT 1")
        group_row = cursor.fetchone()
        admin_group_id = int(group_row["group_id"] if isinstance(group_row, dict) else group_row[0]) if group_row else None
        if admin_group_id is not None:
            cursor.execute("DELETE FROM user_permission_groups WHERE user_id = ?", (user_id,))
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_permission_groups (user_id, group_id, created_at_ms)
                VALUES (?, ?, ?)
                """,
                (user_id, admin_group_id, now_ms),
            )

        conn.commit()
    finally:
        conn.close()

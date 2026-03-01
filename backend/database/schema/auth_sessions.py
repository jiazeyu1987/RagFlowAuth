from __future__ import annotations

import sqlite3

from .helpers import table_exists


def ensure_auth_login_sessions_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "auth_login_sessions"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_login_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            refresh_jti TEXT,
            created_at_ms INTEGER NOT NULL,
            last_activity_at_ms INTEGER NOT NULL,
            last_refresh_at_ms INTEGER,
            expires_at_ms INTEGER,
            revoked_at_ms INTEGER,
            revoked_reason TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_login_sessions_user_id ON auth_login_sessions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_login_sessions_active ON auth_login_sessions(user_id, revoked_at_ms)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_login_sessions_expires ON auth_login_sessions(expires_at_ms)")

from __future__ import annotations

import sqlite3

from .helpers import table_exists


def ensure_chat_sessions_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "chat_sessions"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at_ms INTEGER NOT NULL,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            deleted_at_ms INTEGER,
            deleted_by TEXT,
            UNIQUE(session_id, chat_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_session ON chat_sessions(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_chat ON chat_sessions(chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_deleted ON chat_sessions(is_deleted)")


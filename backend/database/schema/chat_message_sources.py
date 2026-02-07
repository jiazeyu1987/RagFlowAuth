from __future__ import annotations

import sqlite3

from .helpers import table_exists


def ensure_chat_message_sources_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "chat_message_sources"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_message_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            sources_json TEXT NOT NULL,
            created_at_ms INTEGER NOT NULL,
            updated_at_ms INTEGER NOT NULL,
            UNIQUE(chat_id, session_id, content_hash)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_msg_sources_chat ON chat_message_sources(chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_msg_sources_session ON chat_message_sources(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_msg_sources_hash ON chat_message_sources(content_hash)")


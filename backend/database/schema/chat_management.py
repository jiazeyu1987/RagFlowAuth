from __future__ import annotations

import sqlite3

from .helpers import table_exists


def ensure_chat_ownerships_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "chat_ownerships"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_ownerships (
            chat_id TEXT PRIMARY KEY,
            created_by TEXT NOT NULL,
            created_at_ms INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_ownerships_created_by
        ON chat_ownerships(created_by)
        """
    )

from __future__ import annotations

import sqlite3

from .helpers import table_exists


def ensure_search_configs_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "search_configs"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS search_configs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            config_json TEXT NOT NULL,
            created_at_ms INTEGER NOT NULL,
            updated_at_ms INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_search_configs_name ON search_configs(name)")

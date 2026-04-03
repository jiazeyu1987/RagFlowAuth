from __future__ import annotations

import sqlite3

from .helpers import table_exists


def ensure_config_change_logs_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "config_change_logs"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS config_change_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_domain TEXT NOT NULL,
            before_json TEXT NOT NULL,
            after_json TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            change_reason TEXT NOT NULL,
            approved_by TEXT,
            created_at_ms INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_config_change_logs_domain_created ON config_change_logs(config_domain, created_at_ms DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_config_change_logs_changed_by ON config_change_logs(changed_by)")

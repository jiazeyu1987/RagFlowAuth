from __future__ import annotations

import json
import sqlite3

from .helpers import table_exists


def ensure_upload_settings_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "upload_settings"):
        conn.execute(
            """
            CREATE TABLE upload_settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )

    cur = conn.execute("SELECT 1 FROM upload_settings WHERE key = ? LIMIT 1", ("allowed_extensions",))
    if cur.fetchone():
        return

    conn.execute(
        """
        INSERT INTO upload_settings (key, value_json, updated_at_ms)
        VALUES (?, ?, strftime('%s','now') * 1000)
        """,
        (
            "allowed_extensions",
            json.dumps(
                [
                    ".txt",
                    ".pdf",
                    ".docx",
                    ".md",
                    ".xlsx",
                    ".xls",
                    ".csv",
                    ".png",
                    ".jpg",
                    ".jpeg",
                ],
                ensure_ascii=False,
            ),
        ),
    )

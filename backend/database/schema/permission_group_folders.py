from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_permission_group_folders_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "permission_group_folders"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS permission_group_folders (
                folder_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parent_id TEXT,
                created_by TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                FOREIGN KEY(parent_id) REFERENCES permission_group_folders(folder_id) ON DELETE CASCADE
            )
            """
        )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pg_folders_parent_name
        ON permission_group_folders(COALESCE(parent_id, ''), name COLLATE NOCASE)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pg_folders_parent
        ON permission_group_folders(parent_id)
        """
    )


def ensure_permission_groups_folder_column(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "permission_groups"):
        return
    add_column_if_missing(conn, "permission_groups", "folder_id TEXT")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_permission_groups_folder_id
        ON permission_groups(folder_id)
        """
    )

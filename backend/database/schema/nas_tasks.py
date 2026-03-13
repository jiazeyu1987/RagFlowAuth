from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_nas_import_tasks_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "nas_import_tasks"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nas_import_tasks (
                task_id TEXT PRIMARY KEY,
                folder_path TEXT NOT NULL,
                kb_ref TEXT NOT NULL,
                total_files INTEGER NOT NULL DEFAULT 0,
                processed_files INTEGER NOT NULL DEFAULT 0,
                imported_count INTEGER NOT NULL DEFAULT 0,
                skipped_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                current_file TEXT,
                error TEXT,
                imported_json TEXT NOT NULL DEFAULT '[]',
                skipped_json TEXT NOT NULL DEFAULT '[]',
                failed_json TEXT NOT NULL DEFAULT '[]',
                pending_files_json TEXT NOT NULL DEFAULT '[]',
                retry_count INTEGER NOT NULL DEFAULT 0,
                cancel_requested_at_ms INTEGER,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    else:
        add_column_if_missing(conn, "nas_import_tasks", "pending_files_json TEXT NOT NULL DEFAULT '[]'")
        add_column_if_missing(conn, "nas_import_tasks", "retry_count INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "nas_import_tasks", "cancel_requested_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_nas_import_tasks_updated_at ON nas_import_tasks(updated_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_nas_import_tasks_status_updated ON nas_import_tasks(status, updated_at_ms DESC)"
    )

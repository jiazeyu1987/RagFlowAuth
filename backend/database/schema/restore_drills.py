from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_restore_drills_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "restore_drills"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS restore_drills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drill_id TEXT NOT NULL UNIQUE,
                job_id INTEGER NOT NULL,
                backup_path TEXT NOT NULL,
                backup_hash TEXT NOT NULL,
                actual_backup_hash TEXT,
                hash_match INTEGER NOT NULL DEFAULT 0,
                restore_target TEXT NOT NULL,
                restored_auth_db_path TEXT,
                restored_auth_db_hash TEXT,
                compare_match INTEGER NOT NULL DEFAULT 0,
                package_validation_status TEXT,
                acceptance_status TEXT,
                executed_by TEXT NOT NULL,
                executed_at_ms INTEGER NOT NULL,
                result TEXT NOT NULL,
                verification_notes TEXT,
                verification_report_json TEXT
            )
            """
        )
    add_column_if_missing(conn, "restore_drills", "drill_id TEXT")
    add_column_if_missing(conn, "restore_drills", "job_id INTEGER")
    add_column_if_missing(conn, "restore_drills", "backup_path TEXT")
    add_column_if_missing(conn, "restore_drills", "backup_hash TEXT")
    add_column_if_missing(conn, "restore_drills", "actual_backup_hash TEXT")
    add_column_if_missing(conn, "restore_drills", "hash_match INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "restore_drills", "restore_target TEXT")
    add_column_if_missing(conn, "restore_drills", "restored_auth_db_path TEXT")
    add_column_if_missing(conn, "restore_drills", "restored_auth_db_hash TEXT")
    add_column_if_missing(conn, "restore_drills", "compare_match INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "restore_drills", "package_validation_status TEXT")
    add_column_if_missing(conn, "restore_drills", "acceptance_status TEXT")
    add_column_if_missing(conn, "restore_drills", "executed_by TEXT")
    add_column_if_missing(conn, "restore_drills", "executed_at_ms INTEGER")
    add_column_if_missing(conn, "restore_drills", "result TEXT")
    add_column_if_missing(conn, "restore_drills", "verification_notes TEXT")
    add_column_if_missing(conn, "restore_drills", "verification_report_json TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_restore_drills_executed_at ON restore_drills(executed_at_ms DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_restore_drills_job_id ON restore_drills(job_id)")

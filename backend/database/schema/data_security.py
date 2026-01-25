from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_data_security_settings_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "data_security_settings"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS data_security_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            enabled INTEGER NOT NULL DEFAULT 0,
            interval_minutes INTEGER NOT NULL DEFAULT 1440,
            target_mode TEXT NOT NULL DEFAULT 'share',
            target_ip TEXT,
            target_share_name TEXT,
            target_subdir TEXT,
            target_local_dir TEXT,
            ragflow_compose_path TEXT,
            ragflow_project_name TEXT,
            ragflow_stop_services INTEGER NOT NULL DEFAULT 0,
            auth_db_path TEXT NOT NULL DEFAULT 'data/auth.db',
            updated_at_ms INTEGER NOT NULL DEFAULT 0,
            last_run_at_ms INTEGER
        )
        """
    )
    conn.execute("INSERT OR IGNORE INTO data_security_settings (id) VALUES (1)")


def ensure_backup_jobs_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "backup_jobs"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS backup_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL DEFAULT 'incremental',
            status TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            message TEXT,
            detail TEXT,
            output_dir TEXT,
            created_at_ms INTEGER NOT NULL,
            started_at_ms INTEGER,
            finished_at_ms INTEGER
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_backup_jobs_created ON backup_jobs(created_at_ms)")


def ensure_backup_locks_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "backup_locks"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS backup_locks (
            name TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            job_id INTEGER,
            acquired_at_ms INTEGER NOT NULL
        )
        """
    )


def add_backup_job_kind_column(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "backup_jobs"):
        return
    add_column_if_missing(conn, "backup_jobs", "kind TEXT NOT NULL DEFAULT 'incremental'")


def add_full_backup_columns_to_data_security(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "data_security_settings"):
        return
    add_column_if_missing(conn, "data_security_settings", "full_backup_enabled INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "data_security_settings", "full_backup_include_images INTEGER NOT NULL DEFAULT 1")


def add_cron_schedule_columns_to_data_security(conn: sqlite3.Connection) -> None:
    """Add cron-based scheduling columns to data_security_settings table."""
    if not table_exists(conn, "data_security_settings"):
        return
    add_column_if_missing(conn, "data_security_settings", "incremental_schedule TEXT")
    add_column_if_missing(conn, "data_security_settings", "full_backup_schedule TEXT")


def add_last_backup_time_columns_to_data_security(conn: sqlite3.Connection) -> None:
    """Add last backup time tracking columns to prevent missed backups after restart."""
    if not table_exists(conn, "data_security_settings"):
        return
    add_column_if_missing(conn, "data_security_settings", "last_incremental_backup_time_ms INTEGER")
    add_column_if_missing(conn, "data_security_settings", "last_full_backup_time_ms INTEGER")

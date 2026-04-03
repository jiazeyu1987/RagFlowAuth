from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_notification_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "notification_channels"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_channels (
                channel_id TEXT PRIMARY KEY,
                channel_type TEXT NOT NULL,
                name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                config_json TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "notification_channels", "channel_type TEXT")
    add_column_if_missing(conn, "notification_channels", "name TEXT")
    add_column_if_missing(conn, "notification_channels", "enabled INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "notification_channels", "config_json TEXT")
    add_column_if_missing(conn, "notification_channels", "created_at_ms INTEGER")
    add_column_if_missing(conn, "notification_channels", "updated_at_ms INTEGER")

    if not table_exists(conn, "notification_jobs"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_jobs (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                recipient_user_id TEXT,
                recipient_username TEXT,
                recipient_address TEXT,
                dedupe_key TEXT,
                source_job_id INTEGER,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                last_error TEXT,
                created_at_ms INTEGER NOT NULL,
                sent_at_ms INTEGER,
                next_retry_at_ms INTEGER,
                read_at_ms INTEGER
            )
            """
        )
    add_column_if_missing(conn, "notification_jobs", "channel_id TEXT")
    add_column_if_missing(conn, "notification_jobs", "event_type TEXT")
    add_column_if_missing(conn, "notification_jobs", "payload_json TEXT")
    add_column_if_missing(conn, "notification_jobs", "recipient_user_id TEXT")
    add_column_if_missing(conn, "notification_jobs", "recipient_username TEXT")
    add_column_if_missing(conn, "notification_jobs", "recipient_address TEXT")
    add_column_if_missing(conn, "notification_jobs", "dedupe_key TEXT")
    add_column_if_missing(conn, "notification_jobs", "source_job_id INTEGER")
    add_column_if_missing(conn, "notification_jobs", "status TEXT")
    add_column_if_missing(conn, "notification_jobs", "attempts INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "notification_jobs", "max_attempts INTEGER NOT NULL DEFAULT 3")
    add_column_if_missing(conn, "notification_jobs", "last_error TEXT")
    add_column_if_missing(conn, "notification_jobs", "created_at_ms INTEGER")
    add_column_if_missing(conn, "notification_jobs", "sent_at_ms INTEGER")
    add_column_if_missing(conn, "notification_jobs", "next_retry_at_ms INTEGER")
    add_column_if_missing(conn, "notification_jobs", "read_at_ms INTEGER")

    if not table_exists(conn, "notification_delivery_logs"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_delivery_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                channel_id TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                attempted_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "notification_delivery_logs", "job_id INTEGER")
    add_column_if_missing(conn, "notification_delivery_logs", "channel_id TEXT")
    add_column_if_missing(conn, "notification_delivery_logs", "status TEXT")
    add_column_if_missing(conn, "notification_delivery_logs", "error TEXT")
    add_column_if_missing(conn, "notification_delivery_logs", "attempted_at_ms INTEGER")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_notification_channels_enabled ON notification_channels(enabled)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notification_jobs_status ON notification_jobs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notification_jobs_retry ON notification_jobs(next_retry_at_ms)")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notification_jobs_inbox_lookup
        ON notification_jobs(recipient_user_id, channel_id, status, read_at_ms, created_at_ms)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notification_jobs_dedupe
        ON notification_jobs(channel_id, event_type, recipient_user_id, dedupe_key)
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notification_delivery_logs_job ON notification_delivery_logs(job_id)")

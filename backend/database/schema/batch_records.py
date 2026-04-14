from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_batch_records_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "batch_record_templates"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_record_templates (
                template_id TEXT PRIMARY KEY,
                template_code TEXT NOT NULL,
                template_name TEXT NOT NULL,
                version_no INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                steps_json TEXT NOT NULL,
                meta_json TEXT NOT NULL DEFAULT '{}',
                created_by_user_id TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )

    add_column_if_missing(conn, "batch_record_templates", "template_code TEXT")
    add_column_if_missing(conn, "batch_record_templates", "template_name TEXT")
    add_column_if_missing(conn, "batch_record_templates", "version_no INTEGER")
    add_column_if_missing(conn, "batch_record_templates", "status TEXT NOT NULL DEFAULT 'draft'")
    add_column_if_missing(conn, "batch_record_templates", "steps_json TEXT")
    add_column_if_missing(conn, "batch_record_templates", "meta_json TEXT NOT NULL DEFAULT '{}'")
    add_column_if_missing(conn, "batch_record_templates", "created_by_user_id TEXT")
    add_column_if_missing(conn, "batch_record_templates", "created_at_ms INTEGER")
    add_column_if_missing(conn, "batch_record_templates", "updated_at_ms INTEGER")

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_batch_record_templates_code_version "
        "ON batch_record_templates(template_code, version_no)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch_record_templates_code_status "
        "ON batch_record_templates(template_code, status, version_no)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch_record_templates_updated_at "
        "ON batch_record_templates(updated_at_ms DESC)"
    )

    if not table_exists(conn, "batch_record_executions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_record_executions (
                execution_id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                template_code TEXT NOT NULL,
                template_version_no INTEGER NOT NULL,
                title TEXT NOT NULL,
                batch_no TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_progress',
                started_at_ms INTEGER NOT NULL,
                completed_at_ms INTEGER,
                signed_signature_id TEXT,
                reviewed_signature_id TEXT,
                created_by_user_id TEXT NOT NULL,
                updated_by_user_id TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )

    add_column_if_missing(conn, "batch_record_executions", "template_id TEXT")
    add_column_if_missing(conn, "batch_record_executions", "template_code TEXT")
    add_column_if_missing(conn, "batch_record_executions", "template_version_no INTEGER")
    add_column_if_missing(conn, "batch_record_executions", "title TEXT")
    add_column_if_missing(conn, "batch_record_executions", "batch_no TEXT")
    add_column_if_missing(conn, "batch_record_executions", "status TEXT NOT NULL DEFAULT 'in_progress'")
    add_column_if_missing(conn, "batch_record_executions", "started_at_ms INTEGER")
    add_column_if_missing(conn, "batch_record_executions", "completed_at_ms INTEGER")
    add_column_if_missing(conn, "batch_record_executions", "signed_signature_id TEXT")
    add_column_if_missing(conn, "batch_record_executions", "reviewed_signature_id TEXT")
    add_column_if_missing(conn, "batch_record_executions", "created_by_user_id TEXT")
    add_column_if_missing(conn, "batch_record_executions", "updated_by_user_id TEXT")
    add_column_if_missing(conn, "batch_record_executions", "created_at_ms INTEGER")
    add_column_if_missing(conn, "batch_record_executions", "updated_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch_record_executions_status_updated "
        "ON batch_record_executions(status, updated_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch_record_executions_batch_no "
        "ON batch_record_executions(batch_no)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch_record_executions_template_code "
        "ON batch_record_executions(template_code, template_version_no)"
    )

    if not table_exists(conn, "batch_record_step_entries"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_record_step_entries (
                entry_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                step_key TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_by_user_id TEXT NOT NULL,
                created_by_username TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )

    add_column_if_missing(conn, "batch_record_step_entries", "execution_id TEXT")
    add_column_if_missing(conn, "batch_record_step_entries", "step_key TEXT")
    add_column_if_missing(conn, "batch_record_step_entries", "payload_json TEXT")
    add_column_if_missing(conn, "batch_record_step_entries", "created_by_user_id TEXT")
    add_column_if_missing(conn, "batch_record_step_entries", "created_by_username TEXT")
    add_column_if_missing(conn, "batch_record_step_entries", "created_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch_record_step_entries_execution_time "
        "ON batch_record_step_entries(execution_id, created_at_ms)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_batch_record_step_entries_step_key_time "
        "ON batch_record_step_entries(execution_id, step_key, created_at_ms)"
    )


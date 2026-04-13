from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_maintenance_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "maintenance_records"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS maintenance_records (
                record_id TEXT PRIMARY KEY,
                equipment_id TEXT NOT NULL,
                responsible_user_id TEXT NOT NULL,
                maintenance_type TEXT NOT NULL,
                status TEXT NOT NULL,
                planned_due_date TEXT NOT NULL,
                performed_at_ms INTEGER,
                summary TEXT NOT NULL,
                outcome_summary TEXT,
                next_due_date TEXT,
                attachments_json TEXT NOT NULL,
                record_notes TEXT,
                approval_notes TEXT,
                approved_by_user_id TEXT,
                approved_at_ms INTEGER,
                reminder_sent_at_ms INTEGER,
                reminder_sent_for_due_date TEXT,
                created_by_user_id TEXT NOT NULL,
                updated_by_user_id TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "maintenance_records", "equipment_id TEXT")
    add_column_if_missing(conn, "maintenance_records", "responsible_user_id TEXT")
    add_column_if_missing(conn, "maintenance_records", "maintenance_type TEXT")
    add_column_if_missing(conn, "maintenance_records", "status TEXT")
    add_column_if_missing(conn, "maintenance_records", "planned_due_date TEXT")
    add_column_if_missing(conn, "maintenance_records", "performed_at_ms INTEGER")
    add_column_if_missing(conn, "maintenance_records", "summary TEXT")
    add_column_if_missing(conn, "maintenance_records", "outcome_summary TEXT")
    add_column_if_missing(conn, "maintenance_records", "next_due_date TEXT")
    add_column_if_missing(conn, "maintenance_records", "attachments_json TEXT")
    add_column_if_missing(conn, "maintenance_records", "record_notes TEXT")
    add_column_if_missing(conn, "maintenance_records", "approval_notes TEXT")
    add_column_if_missing(conn, "maintenance_records", "approved_by_user_id TEXT")
    add_column_if_missing(conn, "maintenance_records", "approved_at_ms INTEGER")
    add_column_if_missing(conn, "maintenance_records", "reminder_sent_at_ms INTEGER")
    add_column_if_missing(conn, "maintenance_records", "reminder_sent_for_due_date TEXT")
    add_column_if_missing(conn, "maintenance_records", "created_by_user_id TEXT")
    add_column_if_missing(conn, "maintenance_records", "updated_by_user_id TEXT")
    add_column_if_missing(conn, "maintenance_records", "created_at_ms INTEGER")
    add_column_if_missing(conn, "maintenance_records", "updated_at_ms INTEGER")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_records_status ON maintenance_records(status)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_maintenance_records_equipment_updated "
        "ON maintenance_records(equipment_id, updated_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_maintenance_records_due "
        "ON maintenance_records(planned_due_date, next_due_date)"
    )

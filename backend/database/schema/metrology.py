from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_metrology_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "metrology_records"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrology_records (
                record_id TEXT PRIMARY KEY,
                equipment_id TEXT NOT NULL,
                responsible_user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                planned_due_date TEXT NOT NULL,
                performed_at_ms INTEGER,
                result_status TEXT,
                summary TEXT NOT NULL,
                next_due_date TEXT,
                attachments_json TEXT NOT NULL,
                record_notes TEXT,
                confirmation_notes TEXT,
                approval_notes TEXT,
                confirmed_by_user_id TEXT,
                confirmed_at_ms INTEGER,
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
    add_column_if_missing(conn, "metrology_records", "equipment_id TEXT")
    add_column_if_missing(conn, "metrology_records", "responsible_user_id TEXT")
    add_column_if_missing(conn, "metrology_records", "status TEXT")
    add_column_if_missing(conn, "metrology_records", "planned_due_date TEXT")
    add_column_if_missing(conn, "metrology_records", "performed_at_ms INTEGER")
    add_column_if_missing(conn, "metrology_records", "result_status TEXT")
    add_column_if_missing(conn, "metrology_records", "summary TEXT")
    add_column_if_missing(conn, "metrology_records", "next_due_date TEXT")
    add_column_if_missing(conn, "metrology_records", "attachments_json TEXT")
    add_column_if_missing(conn, "metrology_records", "record_notes TEXT")
    add_column_if_missing(conn, "metrology_records", "confirmation_notes TEXT")
    add_column_if_missing(conn, "metrology_records", "approval_notes TEXT")
    add_column_if_missing(conn, "metrology_records", "confirmed_by_user_id TEXT")
    add_column_if_missing(conn, "metrology_records", "confirmed_at_ms INTEGER")
    add_column_if_missing(conn, "metrology_records", "approved_by_user_id TEXT")
    add_column_if_missing(conn, "metrology_records", "approved_at_ms INTEGER")
    add_column_if_missing(conn, "metrology_records", "reminder_sent_at_ms INTEGER")
    add_column_if_missing(conn, "metrology_records", "reminder_sent_for_due_date TEXT")
    add_column_if_missing(conn, "metrology_records", "created_by_user_id TEXT")
    add_column_if_missing(conn, "metrology_records", "updated_by_user_id TEXT")
    add_column_if_missing(conn, "metrology_records", "created_at_ms INTEGER")
    add_column_if_missing(conn, "metrology_records", "updated_at_ms INTEGER")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_metrology_records_status ON metrology_records(status)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_metrology_records_equipment_updated "
        "ON metrology_records(equipment_id, updated_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_metrology_records_due "
        "ON metrology_records(planned_due_date, next_due_date)"
    )
